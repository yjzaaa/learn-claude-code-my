"""运行时上下文：用于在工具层访问当前 dialog_id。"""

from __future__ import annotations

from contextvars import ContextVar, Token


_CURRENT_DIALOG_ID: ContextVar[str | None] = ContextVar("current_dialog_id", default=None)


def set_current_dialog_id(dialog_id: str | None) -> Token[str | None]:
    return _CURRENT_DIALOG_ID.set(dialog_id)


def reset_current_dialog_id(token: Token[str | None]) -> None:
    _CURRENT_DIALOG_ID.reset(token)


def get_current_dialog_id() -> str | None:
    return _CURRENT_DIALOG_ID.get()
