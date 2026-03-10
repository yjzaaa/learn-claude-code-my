"""将多个 hook 委托组合为单一生命周期委托。"""

from __future__ import annotations

from typing import Any

from loguru import logger

try:
    from ...base.abstract import AgentLifecycleHooks, HookName
except ImportError:
    from agents.base.abstract import AgentLifecycleHooks, HookName


class CompositeHooks(AgentLifecycleHooks):
    """按顺序将每次 hook 调用转发给所有委托。"""

    def __init__(self, delegates: list[AgentLifecycleHooks]):
        self._delegates = delegates

    def on_hook(self, hook: HookName, **payload: Any) -> None:
        logger.debug(
            f"[CompositeHooks] on_hook called: hook={hook}, delegates={len(self._delegates)}, "
            f"payload_keys={list(payload.keys())}"
        )
        for i, delegate in enumerate(self._delegates):
            try:
                logger.debug(f"[CompositeHooks] Calling delegate {i}: {type(delegate).__name__}")
                delegate.on_hook(hook, **payload)
            except Exception as e:
                logger.error(f"[CompositeHooks] Error in delegate {i}: {e}")
                import traceback
                logger.error(traceback.format_exc())
