"""运行时上下文：用于在工具层访问当前 dialog_id。"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any


_CURRENT_DIALOG_ID: ContextVar[str | None] = ContextVar("current_dialog_id", default=None)
_MONITORING_BRIDGE: ContextVar[Any | None] = ContextVar("monitoring_bridge", default=None)


def set_current_dialog_id(dialog_id: str | None) -> Token[str | None]:
    return _CURRENT_DIALOG_ID.set(dialog_id)


def reset_current_dialog_id(token: Token[str | None]) -> None:
    _CURRENT_DIALOG_ID.reset(token)


def get_current_dialog_id() -> str | None:
    return _CURRENT_DIALOG_ID.get()


def set_current_monitoring_bridge(bridge: Any | None) -> Token[Any | None]:
    """设置当前的 monitoring bridge，供工具层发送监控事件。"""
    return _MONITORING_BRIDGE.set(bridge)


def reset_current_monitoring_bridge(token: Token[Any | None]) -> None:
    """重置 monitoring bridge。"""
    _MONITORING_BRIDGE.reset(token)


def get_current_monitoring_bridge() -> Any | None:
    """获取当前的 monitoring bridge。"""
    return _MONITORING_BRIDGE.get()
