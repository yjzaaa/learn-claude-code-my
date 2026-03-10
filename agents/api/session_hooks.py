"""Compatibility exports for hook classes moved under agents.hooks."""

from __future__ import annotations

try:
    from ..hooks.composite.composite_hooks import CompositeHooks
    from ..hooks.session_history_hook import SessionHistoryHook
    from ..session.session_manager import SessionManager
except ImportError:
    from agents.hooks.composite.composite_hooks import CompositeHooks
    from agents.hooks.session_history_hook import SessionHistoryHook
    from agents.session.session_manager import SessionManager


class SessionHistoryHooks(CompositeHooks):
    """Backward-compatible wrapper around merged session history hook."""

    def __init__(self, dialog_id: str, session_manager: SessionManager):
        history_hook = SessionHistoryHook(
            dialog_id=dialog_id,
            session_manager=session_manager,
        )
        super().__init__([history_hook])
