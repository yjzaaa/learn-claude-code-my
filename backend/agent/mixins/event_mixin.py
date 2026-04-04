"""
事件相关功能的 Mixin
"""

from typing import Callable, Any

from .base import EngineMixinBase


class EventMixin(EngineMixinBase):
    """事件订阅和发射功能"""

    def subscribe(
        self,
        callback: Callable,
        event_types: list[str] | None = None,
        dialog_id: str | None = None
    ) -> Callable:
        """
        订阅事件

        Args:
            callback: 回调函数
            event_types: 事件类型列表
            dialog_id: 特定对话 ID

        Returns:
            取消订阅函数
        """
        return self._event_bus.subscribe(callback, event_types, dialog_id)

    def emit(self, event: Any):
        """
        发射事件

        Args:
            event: 事件对象
        """
        self._event_bus.emit(event)

    @property
    def event_bus(self) -> "Any":
        """事件总线 (高级用例)"""
        return self._event_bus
