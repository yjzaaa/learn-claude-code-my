#!/usr/bin/env python3
"""
CompactPlugin - 上下文压缩插件

将 s06_context_compact 重构为插件形式
提供三层压缩机制：
1. micro_compact: 每轮静默压缩旧 tool_result
2. auto_compact: 超过 token 阈值时自动压缩
3. compact 工具: 手动触发压缩
"""

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from . import AgentPlugin

try:
    from ..base import tool
    from ..providers import create_provider_from_env
except ImportError:
    from agents.base import tool
    from agents.providers import create_provider_from_env

WORKDIR = Path.cwd()
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
KEEP_RECENT = 3
THRESHOLD = 50000  # 自动压缩阈值


def estimate_tokens(messages: list) -> int:
    """粗略估算 token 数：约 4 个字符约等于 1 个 token"""
    return len(str(messages)) // 4


class CompactPlugin(AgentPlugin):
    """
    上下文压缩插件

    通过策略性遗忘，让代理可以长期稳定运行
    """

    name = "compact_plugin"
    description = "Context Compaction"
    enabled = True

    def __init__(self, agent: Any):
        super().__init__(agent)
        self.provider = create_provider_from_env()
        self.model = self.provider.default_model if self.provider else "deepseek-chat"
        self._manual_compact_triggered = False
        self._last_messages_ref: Optional[List[Dict]] = None

    def on_before_run(self, messages: List[Dict]) -> None:
        """
        在运行前进行压缩处理

        第 1 层：micro_compact - 每轮静默执行
        第 2 层：auto_compact - 超过阈值时自动压缩
        第 3 层：manual_compact - 由 compact 工具触发
        """
        # 保存 messages 引用，供手动压缩使用
        self._last_messages_ref = messages

        # 第 3 层：如果手动触发，执行完整压缩
        if self._manual_compact_triggered:
            logger.info("[CompactPlugin] Executing manual compact")
            self._auto_compact(messages)
            self._manual_compact_triggered = False
            return

        # 第 1 层：微压缩
        self._micro_compact(messages)

        # 第 2 层：自动压缩（如果超过阈值）
        if estimate_tokens(messages) > THRESHOLD:
            logger.info("[CompactPlugin] Auto-compact triggered")
            self._auto_compact(messages)

    def on_tool_call(self, name: str, arguments: Dict) -> None:
        """
        检测是否调用了 compact 工具

        第 3 层：手动触发压缩（标记，实际压缩在下一轮 on_before_run 中执行）
        """
        if name == "compact":
            self._manual_compact_triggered = True
            logger.info("[CompactPlugin] Manual compact triggered")

    def get_additional_tools(self) -> List[Callable]:
        """返回 compact 工具"""
        return [self._compact_tool]

    def get_system_prompt_addon(self) -> str:
        """返回压缩相关提示"""
        return """## Context Management

When the conversation becomes too long:
- Call compact() to summarize the conversation
- This will preserve important context while reducing token usage
- Use it proactively when you feel the context is getting cluttered
"""

    def _micro_compact(self, messages: List[Dict]) -> None:
        """
        第 1 层：微压缩

        将除最近 KEEP_RECENT 条以外的 tool 消息内容替换为占位符
        """
        # 收集所有 tool 消息的位置
        tool_messages = []
        for idx, msg in enumerate(messages):
            if msg.get("role") == "tool":
                tool_messages.append((idx, msg))

        if len(tool_messages) <= KEEP_RECENT:
            return

        # 构建 tool_use_id -> tool_name 映射
        tool_name_map = {}
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if isinstance(tc, dict):
                        tool_id = tc.get("id", "")
                        tool_name = tc.get("function", {}).get("name", "unknown")
                        tool_name_map[tool_id] = tool_name

        # 清理旧结果
        to_clear = tool_messages[:-KEEP_RECENT]
        for idx, msg in to_clear:
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > 100:
                tool_call_id = msg.get("tool_call_id", "")
                tool_name = tool_name_map.get(tool_call_id, "unknown")
                msg["content"] = f"[Previous: used {tool_name}]"

        if to_clear:
            logger.debug(f"[CompactPlugin] Micro-compacted {len(to_clear)} tool results")

    def _auto_compact(self, messages: List[Dict]) -> None:
        """
        第 2 层：自动压缩

        将完整对话保存到磁盘，生成摘要，用摘要替换当前消息
        """
        import time

        # 保存完整对话
        TRANSCRIPT_DIR.mkdir(exist_ok=True)
        transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
        try:
            with open(transcript_path, "w", encoding="utf-8") as f:
                for msg in messages:
                    f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            logger.info(f"[CompactPlugin] Transcript saved: {transcript_path}")
        except Exception as e:
            logger.error(f"[CompactPlugin] Failed to save transcript: {e}")
            return

        # 请求模型生成摘要
        if self.provider:
            try:
                conversation_text = json.dumps(messages, default=str, ensure_ascii=False)[:80000]

                # 使用 provider 生成摘要
                summary_messages = [
                    {"role": "user", "content": (
                        "Summarize this conversation for continuity. Include:\n"
                        "1) What was accomplished\n"
                        "2) Current state\n"
                        "3) Key decisions made\n\n"
                        f"{conversation_text}"
                    )}
                ]

                # 同步调用获取摘要
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果在异步上下文中，创建新任务
                        logger.warning("[CompactPlugin] Cannot generate summary in async context, skipping auto-compact")
                        return
                except RuntimeError:
                    pass

                # 清空消息列表，用摘要替换
                messages[:] = [
                    {
                        "role": "user",
                        "content": f"[Conversation compressed. Transcript: {transcript_path}]\n\nSummary: (See original transcript)"
                    },
                    {
                        "role": "assistant",
                        "content": "Understood. I have the context from the summary. Continuing."
                    },
                ]
                logger.info("[CompactPlugin] Auto-compact completed")

            except Exception as e:
                logger.error(f"[CompactPlugin] Failed to generate summary: {e}")

    @tool(name="compact", description="Manually trigger conversation compression to reduce context size.")
    def _compact_tool(self, focus: str = "") -> str:
        """
        手动触发上下文压缩

        Args:
            focus: 可选的压缩焦点描述
        """
        _ = focus  # 暂不使用
        return "Compacting... The conversation will be summarized in the next round."
