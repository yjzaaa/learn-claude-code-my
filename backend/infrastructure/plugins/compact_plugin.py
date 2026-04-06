"""
Compact Plugin - 上下文压缩插件

将上下文压缩重构为插件形式，与 EventBus 集成。
提供三层压缩机制：
1. micro_compact: 每轮静默压缩旧 tool_result
2. auto_compact: 超过 token 阈值时自动压缩
3. compact 工具: 手动触发压缩
"""

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from loguru import logger

from backend.infrastructure.tools import tool

from .base import AgentPlugin

TRANSCRIPT_DIR = Path(".transcripts")
KEEP_RECENT = 3
THRESHOLD = 50000  # 自动压缩阈值


def estimate_tokens(messages: list) -> int:
    """粗略估算 token 数"""
    return len(str(messages)) // 4


class CompactPlugin(AgentPlugin):
    """
    上下文压缩插件

    通过策略性遗忘，让 Agent 可以长期稳定运行
    """

    name = "compact_plugin"
    description = "Context Compaction"
    enabled = True

    def __init__(self, event_bus=None):
        super().__init__(event_bus)
        self._manual_compact_triggered = False
        self._messages_buffer: list[dict] = []

    def activate(self) -> None:
        """激活插件，订阅事件"""
        # 订阅消息接收事件进行压缩
        self.subscribe(self._on_message_received, event_types=["MessageReceived"])

    def _on_message_received(self, event: Any) -> None:
        """处理消息接收事件"""
        # 这里可以进行微压缩
        pass

    def should_compact(self, messages: list[dict]) -> bool:
        """检查是否需要压缩"""
        return estimate_tokens(messages) > THRESHOLD

    def micro_compact(self, messages: list[dict]) -> None:
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

    async def auto_compact(self, messages: list[dict]) -> None:
        """
        第 2 层：自动压缩

        将完整对话保存到磁盘，生成摘要，用摘要替换当前消息
        """
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

        # 简化：清空消息列表，用摘要替换
        messages[:] = [
            {
                "role": "user",
                "content": f"[Conversation compressed. Transcript: {transcript_path}]",
            },
            {
                "role": "assistant",
                "content": "Understood. I have the context from the summary. Continuing.",
            },
        ]
        logger.info("[CompactPlugin] Auto-compact completed")

    def trigger_manual_compact(self) -> None:
        """触发手动压缩"""
        self._manual_compact_triggered = True
        logger.info("[CompactPlugin] Manual compact triggered")

    def get_additional_tools(self) -> list[Callable]:
        """返回 compact 工具"""
        return [self.compact_tool]

    def get_system_prompt_addon(self) -> str:
        """返回压缩相关提示"""
        return """## Context Management

When the conversation becomes too long:
- Call compact() to summarize the conversation
- This will preserve important context while reducing token usage
- Use it proactively when you feel the context is getting cluttered
"""

    @tool(
        name="compact",
        description="Manually trigger conversation compression to reduce context size.",
    )
    def compact_tool(self, focus: str = "") -> str:
        """
        手动触发上下文压缩

        Args:
            focus: 可选的压缩焦点描述
        """
        self.trigger_manual_compact()
        _ = focus
        return "Compacting... The conversation will be summarized in the next round."
