"""Application Container - 应用状态容器

集中管理全局状态和依赖，替代 main.py 中的全局变量。
遵循依赖注入原则，便于测试和维护。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from fastapi import WebSocket
    from backend.infrastructure.queue import InMemoryAsyncQueue
    from backend.infrastructure.event_bus import QueuedEventBus
    from backend.infrastructure.agent_queue import AgentTaskQueue
    from backend.infrastructure.websocket_buffer import WebSocketMessageBuffer
    from backend.domain.models.dialog import DialogSessionManager


@dataclass
class AppState:
    """应用状态"""
    # HTTP/WebSocket
    ws_clients: set = field(default_factory=set)
    client_buffers: dict[str, Any] = field(default_factory=dict)

    # Dialog State
    status: dict[str, str] = field(default_factory=dict)
    streaming_msg: dict[str, Optional[dict]] = field(default_factory=dict)
    accumulated_content: dict[str, str] = field(default_factory=dict)
    dialog_locks: dict[str, asyncio.Lock] = field(default_factory=dict)

    # Services
    event_bus: Optional[Any] = None
    task_queue: Optional[Any] = None
    session_manager: Optional[Any] = None
    runtime: Optional[Any] = None

    # Config
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    config: Optional[Any] = None


class AppContainer:
    """应用容器 - 单例模式

    Usage:
        from backend.infrastructure.container import container

        # 获取 runtime
        runtime = container.runtime

        # 获取状态
        status = container.state.status.get(dialog_id)
    """

    _instance: Optional[AppContainer] = None

    def __new__(cls) -> AppContainer:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.state = AppState()
        self._initialized = True

    # ═════════════════════════════════════════════════════════════════
    # Property accessors
    # ═════════════════════════════════════════════════════════════════

    @property
    def runtime(self) -> Any:
        """Agent Runtime 实例"""
        return self.state.runtime

    @runtime.setter
    def runtime(self, value: Any) -> None:
        self.state.runtime = value

    @property
    def session_manager(self) -> Any:
        """Session Manager 实例"""
        return self.state.session_manager

    @session_manager.setter
    def session_manager(self, value: Any) -> None:
        self.state.session_manager = value

    @property
    def event_bus(self) -> Optional[Any]:
        """Event Bus 实例"""
        return self.state.event_bus

    @event_bus.setter
    def event_bus(self, value: Optional[Any]) -> None:
        self.state.event_bus = value

    @property
    def task_queue(self) -> Optional[Any]:
        """Agent Task Queue 实例"""
        return self.state.task_queue

    @task_queue.setter
    def task_queue(self, value: Optional[Any]) -> None:
        self.state.task_queue = value

    @property
    def config(self) -> Any:
        """Engine Config"""
        return self.state.config

    @config.setter
    def config(self, value: Any) -> None:
        self.state.config = value

    @property
    def project_root(self) -> Path:
        """项目根目录"""
        return self.state.project_root

    # ═════════════════════════════════════════════════════════════════
    # State helpers
    # ═════════════════════════════════════════════════════════════════

    def get_status(self, dialog_id: str) -> str:
        """获取对话状态"""
        return self.state.status.get(dialog_id, "idle")

    def set_status(self, dialog_id: str, status: str) -> None:
        """设置对话状态"""
        self.state.status[dialog_id] = status

    def get_streaming_message(self, dialog_id: str) -> Optional[dict]:
        """获取流式消息"""
        return self.state.streaming_msg.get(dialog_id)

    def set_streaming_message(self, dialog_id: str, msg: Optional[dict]) -> None:
        """设置流式消息"""
        self.state.streaming_msg[dialog_id] = msg

    def get_accumulated(self, dialog_id: str) -> str:
        """获取累积内容"""
        return self.state.accumulated_content.get(dialog_id, "")

    def set_accumulated(self, dialog_id: str, content: str) -> None:
        """设置累积内容"""
        self.state.accumulated_content[dialog_id] = content

    def append_accumulated(self, dialog_id: str, delta: str) -> str:
        """追加累积内容"""
        current = self.state.accumulated_content.get(dialog_id, "")
        updated = current + delta
        self.state.accumulated_content[dialog_id] = updated
        return updated

    def clear_dialog_state(self, dialog_id: str) -> None:
        """清理对话状态"""
        self.state.status.pop(dialog_id, None)
        self.state.streaming_msg.pop(dialog_id, None)
        self.state.accumulated_content.pop(dialog_id, None)
        self.state.dialog_locks.pop(dialog_id, None)

    def get_dialog_lock(self, dialog_id: str) -> asyncio.Lock:
        """获取对话锁"""
        if dialog_id not in self.state.dialog_locks:
            self.state.dialog_locks[dialog_id] = asyncio.Lock()
        return self.state.dialog_locks[dialog_id]

    def get_ws_buffer(self, client_id: str) -> Optional[Any]:
        """获取 WebSocket 缓冲区"""
        return self.state.client_buffers.get(client_id)

    def set_ws_buffer(self, client_id: str, buffer: Any) -> None:
        """设置 WebSocket 缓冲区"""
        self.state.client_buffers[client_id] = buffer

    def remove_ws_buffer(self, client_id: str) -> None:
        """移除 WebSocket 缓冲区"""
        self.state.client_buffers.pop(client_id, None)


# 全局容器实例
container = AppContainer()


__all__ = ["AppContainer", "AppState", "container"]
