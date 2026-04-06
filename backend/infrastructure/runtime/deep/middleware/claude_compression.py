"""Claude-style Four-Layer Compression Middleware

参考 Claude Code 的上下文压缩机制，实现四层压缩：
1. Micro Compact:   静默替换旧 tool_result 为占位符
2. Auto Compact:    超过 token 阈值时自动触发摘要
3. Partial Compact: 保留最近消息及被引用的关键内容
4. Session Memory:  压缩前将完整对话持久化到 backend 或本地
"""

from __future__ import annotations

import json
from collections.abc import Coroutine
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, overload

from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.runtime import Runtime

from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)

# 若 backend 支持 write 则优先落盘，否则回退到本地
TRANSCRIPT_DIR = Path(".transcripts")
KEEP_RECENT = 20
DEFAULT_THRESHOLD = 100000  # 字符数阈值（约对应 token）


class ClaudeCompressionMiddleware(AgentMiddleware):
    """Claude 风格四层压缩中间件"""

    tools = ()
    _transcript_dir = Path(".transcripts")
    _keep_recent = 20
    _default_threshold = 100000

    def __init__(
        self,
        model: Any,
        backend: Any | None = None,
        threshold: int = _default_threshold,
        keep_recent: int = _keep_recent,
    ) -> None:
        self.model = model
        self.backend = backend
        self.threshold = threshold
        self.keep_recent = keep_recent

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def before_model(self, state: AgentState[Any], runtime: Runtime[Any]) -> dict[str, Any] | None:
        messages = list(state.get("messages", []))
        if not messages:
            logger.debug("[ClaudeCompression] before_model: no messages, skipping")
            return None

        self._log_initial_stats(len(messages), self._estimate_tokens(messages), "before_model")
        return self._perform_compaction(messages, False)

    async def abefore_model(
        self, state: AgentState[Any], runtime: Runtime[Any]
    ) -> dict[str, Any] | None:
        messages = list(state.get("messages", []))
        if not messages:
            logger.debug("[ClaudeCompression] abefore_model: no messages, skipping")
            return None

        self._log_initial_stats(len(messages), self._estimate_tokens(messages), "abefore_model")
        return await self._perform_compaction(messages, True)

    # ═══════════════════════════════════════════════════════════
    # Layer 1: Micro Compact
    # ═══════════════════════════════════════════════════════════

    def _micro_compact(self, messages: list[Any]) -> list[Any]:
        """Layer 1: 将除最近 keep_recent 条以外的 tool 消息内容替换为占位符。"""
        tool_indices = [(i, msg) for i, msg in enumerate(messages) if isinstance(msg, ToolMessage)]
        original_count = len(tool_indices)

        if len(tool_indices) <= self.keep_recent:
            logger.debug(
                f"[ClaudeCompression] Layer 1: {original_count} tool messages, "
                f"no compaction needed (keep {self.keep_recent})"
            )
            return messages

        logger.info(
            f"[ClaudeCompression] Layer 1 Micro Compact: {original_count} tool messages "
            f"-> keeping last {self.keep_recent}"
        )

        # 建立 tool_call_id -> tool_name 映射
        tool_name_map = self._build_tool_name_map(messages)

        to_clear = tool_indices[: -self.keep_recent]
        cleared_count = 0
        for _, msg in to_clear:
            content = msg.content
            if isinstance(content, str) and len(content) > 100:
                tid = getattr(msg, "tool_call_id", "")
                tname = tool_name_map.get(tid, "unknown")
                original_len = len(content)
                msg.content = f"[Previous: used {tname}]"
                cleared_count += 1
                logger.debug(
                    f"[ClaudeCompression]   Compacted tool {tname}: "
                    f"{original_len} chars -> placeholder"
                )

        logger.info(
            f"[ClaudeCompression] Layer 1 completed: " f"{cleared_count} tool messages compacted"
        )
        return messages

    def _build_tool_name_map(self, messages: list[Any]) -> dict[str, str]:
        """建立 tool_call_id -> tool_name 映射。"""
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
        return tool_name_map

    # ═══════════════════════════════════════════════════════════
    # Layer 2-4: Auto/Partial Compact + Session Memory
    # ═══════════════════════════════════════════════════════════

    def _partition_for_compaction(self, messages: list[Any]) -> tuple[list[Any], list[Any]] | None:
        """划分消息并检查是否需要压缩。

        Returns:
            None 如果不需要压缩，否则返回 (to_summarize, preserved) 元组
        """
        # Layer 1
        messages = self._micro_compact(messages)

        # Layer 2
        if self._should_compact(messages):
            logger.debug("[ClaudeCompression] Layer 2: below threshold, no auto-compact needed")
            return None

        to_summarize, preserved = self._partition_messages(messages)
        if not to_summarize:
            logger.debug("[ClaudeCompression] Nothing to summarize")
            return None

        logger.warning(
            f"[ClaudeCompression] Layer 2 Auto Compact triggered! "
            f"Summarizing {len(to_summarize)} messages, keeping {len(preserved)}"
        )
        return to_summarize, preserved

    def _partition_messages(self, messages: list[Any]) -> tuple[list[Any], list[Any]]:
        """Layer 3 (Partial): 划分需要摘要的部分与保留的部分。"""
        # 始终保留 SystemMessage
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        non_system = [m for m in messages if not isinstance(m, SystemMessage)]

        if len(non_system) <= self.keep_recent:
            return [], messages

        to_summarize = non_system[: -self.keep_recent]
        preserved = system_msgs + non_system[-self.keep_recent :]
        return to_summarize, preserved

    @overload
    def _perform_compaction(
        self,
        messages: list[Any],
        is_async: Literal[False],
    ) -> dict[str, Any] | None: ...

    @overload
    def _perform_compaction(
        self,
        messages: list[Any],
        is_async: Literal[True],
    ) -> Coroutine[Any, Any, dict[str, Any] | None]: ...

    def _perform_compaction(
        self,
        messages: list[Any],
        is_async: bool,
    ) -> dict[str, Any] | None | Coroutine[Any, Any, dict[str, Any] | None]:
        """执行压缩的核心逻辑（同步/异步通用）。"""
        partition_result = self._partition_for_compaction(messages)
        if partition_result is None:
            # 异步模式下需要返回 awaitable
            if is_async:
                return self._async_return_messages(messages)
            return {"messages": messages}

        to_summarize, preserved = partition_result

        # Layer 4
        transcript_path = self._save_transcript(messages)
        logger.info(f"[ClaudeCompression] Layer 4: transcript saved to {transcript_path}")

        # 生成摘要（根据 is_async 选择模式）
        if is_async:
            return self._async_compaction_finish(
                len(messages), transcript_path, to_summarize, preserved
            )

        summary = self._create_summary_sync(to_summarize)
        return self._build_compaction_result(len(messages), transcript_path, summary, preserved)

    async def _async_return_messages(self, messages: list[Any]) -> dict[str, Any]:
        """异步模式下返回原始消息（用于跳过压缩的情况）。"""
        return {"messages": messages}

    async def _async_compaction_finish(
        self,
        msg_count: int,
        transcript_path: str,
        to_summarize: list[Any],
        preserved: list[Any],
    ) -> dict[str, Any]:
        """异步完成压缩流程。"""
        summary = await self._acreate_summary(to_summarize)
        return self._build_compaction_result(msg_count, transcript_path, summary, preserved)

    def _build_compaction_result(
        self,
        msg_count: int,
        transcript_path: str,
        summary: str,
        preserved: list[Any],
    ) -> dict[str, Any]:
        """构建压缩结果。"""
        logger.info(f"[ClaudeCompression] Summary generated: {len(summary)} chars")
        new_messages = self._build_compressed_messages(transcript_path, summary, preserved)
        logger.info(
            f"[ClaudeCompression] Compression complete: "
            f"{msg_count} -> {len(new_messages)} messages"
        )
        return {"messages": new_messages}

    def _build_compressed_messages(
        self, transcript_path: str, summary: str, preserved: list[Any]
    ) -> list[Any]:
        """构建压缩后的消息列表。"""
        return [
            SystemMessage(
                content=f"[Conversation compressed at {transcript_path}].\n\nSummary:\n{summary}"
            ),
            *preserved,
        ]

    # ═══════════════════════════════════════════════════════════
    # Utility Methods
    # ═══════════════════════════════════════════════════════════

    def _estimate_tokens(self, messages: list[Any]) -> int:
        """粗略估算：约 4 字符 ≈ 1 token。"""
        return len(str(messages)) // 4

    def _should_compact(self, messages: list[Any]) -> bool:
        """检查是否需要自动压缩。"""
        return self._estimate_tokens(messages) <= self.threshold

    def _log_initial_stats(self, msg_count: int, estimated_tokens: int, method: str) -> None:
        """记录初始统计信息。"""
        logger.info(
            f"[ClaudeCompression] {method}: {msg_count} messages, "
            f"~{estimated_tokens} tokens, threshold={self.threshold}"
        )

    # ═══════════════════════════════════════════════════════════
    # Session Memory (Layer 4)
    # ═══════════════════════════════════════════════════════════

    def _get_transcript_path(self) -> Path:
        """生成基于时间戳的 transcript 路径。"""
        self._transcript_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return self._transcript_dir / f"transcript_{ts}.jsonl"

    def _save_transcript(self, messages: list[Any]) -> str:
        """Layer 4: 保存完整对话到 transcript，优先使用 backend.write。"""
        local_path = self._get_transcript_path()
        content = "\n".join(
            json.dumps(m, ensure_ascii=False, default=self._msg_to_dict) for m in messages
        )

        if self.backend is not None:
            try:
                vpath = f"/conversation_history/{local_path.name}"
                self.backend.write(vpath, content)
                return str(vpath)
            except Exception:
                pass

        try:
            local_path.write_text(content, encoding="utf-8")
        except Exception:
            pass
        return str(local_path)

    def _msg_to_dict(self, msg: Any) -> dict[str, Any]:
        """将 message 对象序列化为字典。"""
        if hasattr(msg, "model_dump"):
            return msg.model_dump()
        if hasattr(msg, "to_dict"):
            return msg.to_dict()
        return {"type": type(msg).__name__, "content": getattr(msg, "content", str(msg))}

    # ═══════════════════════════════════════════════════════════
    # Summary Generation
    # ═══════════════════════════════════════════════════════════

    def _create_summary_sync(self, messages: list[Any]) -> str:
        """同步生成摘要。"""
        prompt = self._build_summary_prompt(messages)
        try:
            response = self.model.invoke(prompt)
            return (
                response.content.strip() if hasattr(response, "content") else str(response).strip()
            )
        except Exception as e:
            return f"Error generating summary: {e}"

    async def _acreate_summary(self, messages: list[Any]) -> str:
        """异步生成摘要。"""
        prompt = self._build_summary_prompt(messages)
        try:
            response = await self.model.ainvoke(prompt)
            return (
                response.content.strip() if hasattr(response, "content") else str(response).strip()
            )
        except Exception as e:
            return f"Error generating summary: {e}"

    def _build_summary_prompt(self, messages: list[Any]) -> str:
        """构建摘要生成提示词。"""
        data = json.dumps(
            [self._msg_to_dict(m) for m in messages], ensure_ascii=False, default=str
        )[:80000]
        return (
            "Summarize the following conversation for continuity. "
            "Include: 1) What was accomplished, 2) Current state, 3) Key decisions made. "
            "Be concise but preserve critical details.\n\n"
            f"{data}"
        )


__all__ = ["ClaudeCompressionMiddleware"]
