"""上下文压缩 Hook：微压缩 + 自动压缩 + 手动压缩触发。"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from loguru import logger

try:
    from ..base.abstract import FullAgentHooks
except ImportError:
    from agents.base.abstract import FullAgentHooks


class ContextCompactHook(FullAgentHooks):
    """在生命周期中执行上下文压缩策略。"""

    def __init__(self, bridge: Any):
        self.bridge = bridge
        self.manual_compact = False
        self.threshold_tokens = self._read_int_env("CONTEXT_COMPACT_THRESHOLD", 50000, minimum=1000)
        self.keep_recent_tool_messages = self._read_int_env("CONTEXT_COMPACT_KEEP_RECENT_TOOLS", 3, minimum=1)
        self.transcript_dir = Path.cwd() / ".transcripts"

    @staticmethod
    def _read_int_env(name: str, default: int, minimum: int) -> int:
        raw = os.getenv(name, str(default))
        try:
            return max(minimum, int(raw))
        except ValueError:
            return default

    @staticmethod
    def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
        """粗略估算 token（约 4 字符 ~= 1 token）。"""
        return len(json.dumps(messages, ensure_ascii=False, default=str)) // 4

    def _micro_compact_tool_messages(self) -> None:
        """微压缩：仅保留最近若干条工具消息全文，其余替换占位文本。"""
        all_tool_msgs = [m for m in self.bridge.session.messages if str(getattr(m, "role", "")) in {"tool", "Role.TOOL"}]
        if len(all_tool_msgs) <= self.keep_recent_tool_messages:
            return

        to_compact = all_tool_msgs[:-self.keep_recent_tool_messages]
        for msg in to_compact:
            content = str(getattr(msg, "content", "") or "")
            if len(content) <= 120:
                continue
            tool_name = getattr(msg, "tool_name", None) or "unknown"
            msg.content = f"[Previous: used {tool_name}]"

    def _save_transcript(self, messages: list[dict[str, Any]]) -> Path:
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = self.transcript_dir / f"transcript_{self.bridge.dialog_id}_{int(time.time())}.jsonl"
        with transcript_path.open("w", encoding="utf-8") as fh:
            for msg in messages:
                fh.write(json.dumps(msg, ensure_ascii=False, default=str))
                fh.write("\n")
        return transcript_path

    def _build_summary(self, messages: list[dict[str, Any]], transcript_path: Path) -> str:
        users = [m.get("content", "") for m in messages if m.get("role") == "user"]
        assistants = [m.get("content", "") for m in messages if m.get("role") == "assistant"]
        last_user = str(users[-1])[:300] if users else ""
        last_assistant = str(assistants[-1])[:300] if assistants else ""
        return (
            f"[Conversation compressed. Transcript: {transcript_path}]\n"
            f"- 历史轮次: {len(self.bridge.history_rounds)}\n"
            f"- 最近用户问题摘要: {last_user}\n"
            f"- 最近助手回复摘要: {last_assistant}\n"
            "请基于以上摘要延续上下文。"
        )

    def _auto_compact(self, messages: list[dict[str, Any]]) -> None:
        """自动压缩：落盘全文后，用摘要替换长历史上下文。"""
        transcript_path = self._save_transcript(messages)
        summary = self._build_summary(messages, transcript_path)

        current_user = None
        if messages and messages[-1].get("role") == "user":
            current_user = str(messages[-1].get("content") or "")

        compacted_messages: list[dict[str, Any]] = [
            {"role": "assistant", "content": summary},
        ]
        if current_user is not None:
            compacted_messages.append({"role": "user", "content": current_user})

        messages[:] = compacted_messages

        # 同步压缩 Bridge 内部历史，避免后续重复超阈值。
        self.bridge.history_rounds = [{
            "user": "[Conversation compressed]",
            "assistant": summary,
        }]
        logger.warning(f"[ContextCompactHook] auto_compact applied, transcript={transcript_path}")

    def on_before_run(self, messages: list[dict[str, Any]]) -> None:
        self._micro_compact_tool_messages()
        if self._estimate_tokens(messages) > self.threshold_tokens:
            self._auto_compact(messages)

    def on_stream_token(self, chunk: Any) -> None:
        _ = chunk

    def on_tool_call(self, name: str, arguments: dict[str, Any], tool_call_id: str = "") -> None:
        _ = name
        _ = arguments
        _ = tool_call_id

    def on_tool_result(
        self,
        name: str,
        result: str,
        assistant_message: dict[str, Any] | None = None,
        tool_call_id: str = "",
    ) -> None:
        _ = result
        _ = assistant_message
        _ = tool_call_id
        if name == "compact":
            self.manual_compact = True

    def on_complete(self, content: str) -> None:
        _ = content

    def on_error(self, error: Exception) -> None:
        _ = error

    def on_after_run(self, messages: list[dict[str, Any]], rounds: int) -> None:
        _ = rounds
        if self.manual_compact:
            self._auto_compact(messages)
            self.manual_compact = False

    def on_stop(self) -> None:
        self.manual_compact = False
