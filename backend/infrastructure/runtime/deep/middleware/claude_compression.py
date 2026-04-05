"""Claude-style Four-Layer Compression Middleware

参考 Claude Code 的上下文压缩机制，实现四层压缩：
1. Micro Compact:   静默替换旧 tool_result 为占位符
2. Auto Compact:    超过 token 阈值时自动触发摘要
3. Partial Compact: 保留最近消息及被引用的关键内容
4. Session Memory:  压缩前将完整对话持久化到 backend 或本地
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.runtime import Runtime

from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)

# 若 backend 支持 write 则优先落盘，否则回退到本地
TRANSCRIPT_DIR = Path(".transcripts")
KEEP_RECENT = 3
DEFAULT_THRESHOLD = 50000  # 字符数阈值（约对应 token）


def _estimate_tokens(messages: list[Any]) -> int:
    """粗略估算：约 4 字符 ≈ 1 token。"""
    return len(str(messages)) // 4


def _micro_compact(messages: list[Any]) -> list[Any]:
    """Layer 1: 将除最近 KEEP_RECENT 条以外的 tool 消息内容替换为占位符。"""
    tool_indices = [
        (i, msg) for i, msg in enumerate(messages) if isinstance(msg, ToolMessage)
    ]
    original_count = len(tool_indices)

    if len(tool_indices) <= KEEP_RECENT:
        logger.debug(f"[ClaudeCompression] Layer 1: {original_count} tool messages, no compaction needed (keep {KEEP_RECENT})")
        return messages

    logger.info(f"[ClaudeCompression] Layer 1 Micro Compact: {original_count} tool messages -> keeping last {KEEP_RECENT}")

    # 建立 tool_call_id -> tool_name 映射
    tool_name_map: dict[str, str] = {}
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if isinstance(tc, dict):
                    tid = tc.get("id", "")
                    tname = tc.get("name", "unknown")
                else:
                    tid = getattr(tc, "id", "")
                    tname = getattr(tc, "name", "unknown")
                if tid:
                    tool_name_map[tid] = tname

    to_clear = tool_indices[:-KEEP_RECENT]
    cleared_count = 0
    for _, msg in to_clear:
        content = msg.content
        if isinstance(content, str) and len(content) > 100:
            tid = getattr(msg, "tool_call_id", "")
            tname = tool_name_map.get(tid, "unknown")
            original_len = len(content)
            msg.content = f"[Previous: used {tname}]"
            cleared_count += 1
            logger.debug(f"[ClaudeCompression]   Compacted tool {tname}: {original_len} chars -> placeholder")

    logger.info(f"[ClaudeCompression] Layer 1 completed: {cleared_count} tool messages compacted")
    return messages


def _get_transcript_path() -> Path:
    """生成基于时间戳的 transcript 路径。"""
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return TRANSCRIPT_DIR / f"transcript_{ts}.jsonl"


def _save_transcript(messages: list[Any], backend: Any | None) -> str:
    """Layer 4: 保存完整对话到 transcript，优先使用 backend.write。"""
    local_path = _get_transcript_path()
    content = "\n".join(json.dumps(m, ensure_ascii=False, default=_msg_to_dict) for m in messages)

    if backend is not None:
        try:
            vpath = f"/conversation_history/{local_path.name}"
            backend.write(vpath, content)
            return str(vpath)
        except Exception:
            pass

    try:
        local_path.write_text(content, encoding="utf-8")
    except Exception:
        pass
    return str(local_path)


def _msg_to_dict(msg: Any) -> dict[str, Any]:
    """将 message 对象序列化为字典。"""
    if hasattr(msg, "model_dump"):
        return msg.model_dump()
    if hasattr(msg, "to_dict"):
        return msg.to_dict()
    return {"type": type(msg).__name__, "content": getattr(msg, "content", str(msg))}


def _partition_messages(messages: list[Any], keep_recent: int = KEEP_RECENT) -> tuple[list[Any], list[Any]]:
    """Layer 3 (Partial): 划分需要摘要的部分与保留的部分。"""
    # 始终保留 SystemMessage
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    non_system = [m for m in messages if not isinstance(m, SystemMessage)]

    if len(non_system) <= keep_recent:
        return [], messages

    to_summarize = non_system[:-keep_recent]
    preserved = system_msgs + non_system[-keep_recent:]
    return to_summarize, preserved


class ClaudeCompressionMiddleware(AgentMiddleware):
    """Claude 风格四层压缩中间件"""

    tools = ()

    def __init__(
        self,
        model: Any,
        backend: Any | None = None,
        threshold: int = DEFAULT_THRESHOLD,
        keep_recent: int = KEEP_RECENT,
    ) -> None:
        self.model = model
        self.backend = backend
        self.threshold = threshold
        self.keep_recent = keep_recent

    def before_model(
        self, state: AgentState[Any], runtime: Runtime[Any]
    ) -> dict[str, Any] | None:
        messages = list(state.get("messages", []))
        if not messages:
            logger.debug("[ClaudeCompression] before_model: no messages, skipping")
            return None

        msg_count = len(messages)
        estimated_tokens = _estimate_tokens(messages)
        logger.info(f"[ClaudeCompression] before_model: {msg_count} messages, ~{estimated_tokens} tokens, threshold={self.threshold}")

        # Layer 1
        messages = _micro_compact(messages)

        # Layer 2: 检查是否触发自动压缩
        if _estimate_tokens(messages) <= self.threshold:
            logger.debug(f"[ClaudeCompression] Layer 2: below threshold, no auto-compact needed")
            return {"messages": messages}

        to_summarize, preserved = _partition_messages(messages, self.keep_recent)
        if not to_summarize:
            logger.debug(f"[ClaudeCompression] Nothing to summarize")
            return {"messages": messages}

        logger.warning(f"[ClaudeCompression] Layer 2 Auto Compact triggered! Summarizing {len(to_summarize)} messages, keeping {len(preserved)}")

        # Layer 4: 保存完整会话
        transcript_path = _save_transcript(messages, self.backend)
        logger.info(f"[ClaudeCompression] Layer 4: transcript saved to {transcript_path}")

        # 生成摘要（同步路径）
        summary = self._create_summary(to_summarize)
        logger.info(f"[ClaudeCompression] Summary generated: {len(summary)} chars")

        new_messages: list[Any] = [
            SystemMessage(
                content=(
                    f"[Conversation compressed at {transcript_path}].\n\n"
                    f"Summary:\n{summary}"
                )
            ),
            *preserved,
        ]
        logger.info(f"[ClaudeCompression] Compression complete: {msg_count} -> {len(new_messages)} messages")
        return {"messages": new_messages}

    async def abefore_model(
        self, state: AgentState[Any], runtime: Runtime[Any]
    ) -> dict[str, Any] | None:
        messages = list(state.get("messages", []))
        if not messages:
            logger.debug("[ClaudeCompression] abefore_model: no messages, skipping")
            return None

        msg_count = len(messages)
        estimated_tokens = _estimate_tokens(messages)
        logger.info(f"[ClaudeCompression] abefore_model: {msg_count} messages, ~{estimated_tokens} tokens, threshold={self.threshold}")

        # Layer 1
        messages = _micro_compact(messages)

        # Layer 2
        if _estimate_tokens(messages) <= self.threshold:
            logger.debug(f"[ClaudeCompression] Layer 2: below threshold, no auto-compact needed")
            return {"messages": messages}

        to_summarize, preserved = _partition_messages(messages, self.keep_recent)
        if not to_summarize:
            logger.debug(f"[ClaudeCompression] Nothing to summarize")
            return {"messages": messages}

        logger.warning(f"[ClaudeCompression] Layer 2 Auto Compact triggered! Summarizing {len(to_summarize)} messages, keeping {len(preserved)}")

        # Layer 4
        transcript_path = _save_transcript(messages, self.backend)
        logger.info(f"[ClaudeCompression] Layer 4: transcript saved to {transcript_path}")

        # 生成摘要（异步路径）
        summary = await self._acreate_summary(to_summarize)
        logger.info(f"[ClaudeCompression] Summary generated: {len(summary)} chars")

        new_messages: list[Any] = [
            SystemMessage(
                content=(
                    f"[Conversation compressed at {transcript_path}].\n\n"
                    f"Summary:\n{summary}"
                )
            ),
            *preserved,
        ]
        logger.info(f"[ClaudeCompression] Compression complete: {msg_count} -> {len(new_messages)} messages")
        return {"messages": new_messages}

    def _create_summary(self, messages: list[Any]) -> str:
        prompt = self._build_summary_prompt(messages)
        try:
            response = self.model.invoke(prompt)
            return response.content.strip() if hasattr(response, "content") else str(response).strip()
        except Exception as e:
            return f"Error generating summary: {e}"

    async def _acreate_summary(self, messages: list[Any]) -> str:
        prompt = self._build_summary_prompt(messages)
        try:
            response = await self.model.ainvoke(prompt)
            return response.content.strip() if hasattr(response, "content") else str(response).strip()
        except Exception as e:
            return f"Error generating summary: {e}"

    @staticmethod
    def _build_summary_prompt(messages: list[Any]) -> str:
        data = json.dumps([_msg_to_dict(m) for m in messages], ensure_ascii=False, default=str)[:80000]
        return (
            "Summarize the following conversation for continuity. "
            "Include: 1) What was accomplished, 2) Current state, 3) Key decisions made. "
            "Be concise but preserve critical details.\n\n"
            f"{data}"
        )


__all__ = ["ClaudeCompressionMiddleware"]
