"""Application Container - 应用状态容器

集中管理全局状态和依赖，替代 main.py 中的全局变量。
遵循依赖注入原则，便于测试和维护。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AppState:
    """应用状态"""

    # HTTP/WebSocket
    ws_clients: set = field(default_factory=set)
    client_buffers: dict[str, Any] = field(default_factory=dict)

    # Dialog State
    status: dict[str, str] = field(default_factory=dict)
    streaming_msg: dict[str, dict | None] = field(default_factory=dict)
    accumulated_content: dict[str, str] = field(default_factory=dict)
    dialog_locks: dict[str, asyncio.Lock] = field(default_factory=dict)
    delta_sequences: dict[str, int] = field(default_factory=dict)  # 递增序列号

    # Services
    event_bus: Any | None = None
    task_queue: Any | None = None
    session_manager: Any | None = None
    runtime: Any | None = None

    # Config
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    config: Any | None = None


class AppContainer:
    """应用容器 - 单例模式

    Usage:
        from backend.infrastructure.container import container

        # 获取 runtime
        runtime = container.runtime

        # 获取状态
        status = container.state.status.get(dialog_id)
    """

    _instance: AppContainer | None = None

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
    def event_bus(self) -> Any | None:
        """Event Bus 实例"""
        return self.state.event_bus

    @event_bus.setter
    def event_bus(self, value: Any | None) -> None:
        self.state.event_bus = value

    @property
    def task_queue(self) -> Any | None:
        """Agent Task Queue 实例"""
        return self.state.task_queue

    @task_queue.setter
    def task_queue(self, value: Any | None) -> None:
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

    def get_streaming_message(self, dialog_id: str) -> dict | None:
        """获取流式消息"""
        return self.state.streaming_msg.get(dialog_id)

    def set_streaming_message(self, dialog_id: str, msg: dict | None) -> None:
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
        self.state.delta_sequences.pop(dialog_id, None)

    def get_dialog_lock(self, dialog_id: str) -> asyncio.Lock:
        """获取对话锁"""
        if dialog_id not in self.state.dialog_locks:
            self.state.dialog_locks[dialog_id] = asyncio.Lock()
        return self.state.dialog_locks[dialog_id]

    def get_and_increment_delta_sequence(self, dialog_id: str) -> int:
        """获取并递增 delta 序列号

        用于 stream:delta 事件的序列号，确保每个 delta 都有唯一的序号，
        避免前端因去重逻辑而丢弃消息。

        Args:
            dialog_id: 对话 ID

        Returns:
            当前序列号（递增后）
        """
        current = self.state.delta_sequences.get(dialog_id, 0)
        current += 1
        self.state.delta_sequences[dialog_id] = current
        return current

    def clear_delta_sequence(self, dialog_id: str) -> None:
        """清理对话的 delta 序列号"""
        self.state.delta_sequences.pop(dialog_id, None)

    def get_ws_buffer(self, client_id: str) -> Any | None:
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
