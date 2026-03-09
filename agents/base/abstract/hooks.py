from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class HookName(str, Enum):
    """Standard hook signal names emitted by agent loops."""

    ON_BEFORE_RUN = "on_before_run"
    ON_STREAM_TOKEN = "on_stream_token"
    ON_TOOL_CALL = "on_tool_call"
    ON_TOOL_RESULT = "on_tool_result"
    ON_COMPLETE = "on_complete"
    ON_ERROR = "on_error"
    ON_AFTER_RUN = "on_after_run"
    ON_STOP = "on_stop"


class AgentLifecycleHooks(ABC):
    """Runtime-enforced hook signal dispatcher contract."""

    @abstractmethod
    def on_hook(self, hook: HookName, **payload: Any) -> None:
        raise NotImplementedError


class FullAgentHooks(AgentLifecycleHooks):
    """Full lifecycle interface with explicit hook methods."""

    @abstractmethod
    def on_before_run(self, messages: list[dict[str, Any]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_stream_token(self, chunk: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_tool_call(self, name: str, arguments: dict[str, Any], tool_call_id: str = "") -> None:
        raise NotImplementedError

    @abstractmethod
    def on_tool_result(
        self,
        name: str,
        result: str,
        assistant_message: dict[str, Any] | None = None,
        tool_call_id: str = "",
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_complete(self, content: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_error(self, error: Exception) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_after_run(self, messages: list[dict[str, Any]], rounds: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_stop(self) -> None:
        raise NotImplementedError

    def on_hook(self, hook: HookName, **payload: Any) -> None:
        from loguru import logger
        logger.info(f"[FullAgentHooks] on_hook called: hook={hook}, payload_keys={list(payload.keys())}")
        if hook == HookName.ON_BEFORE_RUN:
            self.on_before_run(payload.get("messages", []))
        elif hook == HookName.ON_STREAM_TOKEN:
            chunk = payload.get("chunk")
            logger.info(f"[FullAgentHooks] ON_STREAM_TOKEN: chunk_type={type(chunk).__name__}, chunk={repr(chunk)[:100] if chunk else 'None'}")
            self.on_stream_token(chunk)
        elif hook == HookName.ON_TOOL_CALL:
            self.on_tool_call(payload.get("name", ""), payload.get("arguments", {}), payload.get("tool_call_id", ""))
        elif hook == HookName.ON_TOOL_RESULT:
            logger.info(f"[FullAgentHooks] ON_TOOL_RESULT: name={payload.get('name', '')}, tool_call_id={payload.get('tool_call_id', '')}")
            self.on_tool_result(
                payload.get("name", ""),
                str(payload.get("result", "")),
                payload.get("assistant_message"),
                str(payload.get("tool_call_id", "")),
            )
        elif hook == HookName.ON_COMPLETE:
            self.on_complete(str(payload.get("content", "")))
        elif hook == HookName.ON_ERROR:
            err = payload.get("error")
            self.on_error(err if isinstance(err, Exception) else Exception(str(err)))
        elif hook == HookName.ON_AFTER_RUN:
            self.on_after_run(payload.get("messages", []), int(payload.get("rounds", 0)))
        elif hook == HookName.ON_STOP:
            self.on_stop()
