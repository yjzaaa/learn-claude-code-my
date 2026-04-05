"""
Todo HITL - Todo 任务管理

管理对话级别的 Todo 列表，支持实时更新和提醒。
"""

from __future__ import annotations

import dataclasses
import os
import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable, Coroutine, Optional

from loguru import logger

from backend.domain.models.api import TodoUpdatedEvent, TodoReminderEvent, TodoStateDTO
from backend.domain.models.shared.types import TodoItemDict


@dataclass
class TodoItem:
    """单个任务项"""
    id: str
    text: str
    status: str  # pending | in_progress | completed

    def to_dict(self) -> TodoItemDict:
        return TodoItemDict(id=self.id, text=self.text, status=self.status)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TodoItem":
        return cls(
            id=str(data["id"]),
            text=str(data["text"]),
            status=str(data["status"]),
        )


@dataclass
class TodoState:
    """对话级别的 Todo 状态"""
    dialog_id: str
    items: list[TodoItem] = field(default_factory=list)
    rounds_since_todo: int = 0
    used_todo_in_round: bool = False
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dialog_id": self.dialog_id,
            "items": [item.to_dict() for item in self.items],
            "rounds_since_todo": self.rounds_since_todo,
            "used_todo_in_round": self.used_todo_in_round,
            "updated_at": self.updated_at,
        }


class TodoStore:
    """管理对话级别的 Todo 状态"""

    # 配置常量
    MAX_ITEMS = int(os.getenv("TODO_MAX_ITEMS", "20"))
    VALID_STATUSES = {"pending", "in_progress", "completed"}
    TODO_REMINDER_ROUNDS = int(os.getenv("TODO_REMINDER_ROUNDS", "3"))

    def __init__(self):
        self._lock = RLock()
        self._states: dict[str, TodoState] = {}
        self._broadcaster: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

    def register_broadcaster(
        self, broadcaster: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        """注册 WebSocket 广播器"""
        self._broadcaster = broadcaster

    def _emit(self, event: dict[str, Any]) -> None:
        """发送事件"""
        if not self._broadcaster:
            return
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcaster(event))
        except RuntimeError:
            pass

    def _validate_items(self, items: list[dict[str, Any]]) -> tuple[bool, str]:
        """
        校验任务列表

        规则：
        - 最多 MAX_ITEMS 项
        - 每项必须有 text
        - status 必须是 pending/in_progress/completed
        - 同一时刻最多 1 条 in_progress
        """
        if len(items) > self.MAX_ITEMS:
            return False, f"Too many items: {len(items)} > {self.MAX_ITEMS}"

        in_progress_count = 0
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                return False, f"Item {i} is not a dict"

            text = item.get("text", "")
            if not text or not str(text).strip():
                return False, f"Item {i} missing text"

            status = item.get("status", "")
            if status not in self.VALID_STATUSES:
                return False, f"Item {i} invalid status: {status}"

            if status == "in_progress":
                in_progress_count += 1

        if in_progress_count > 1:
            return False, f"Multiple in_progress items: {in_progress_count}"

        return True, ""

    def _normalize_items(
        self, items: list[dict[str, Any]]
    ) -> tuple[list[TodoItemDict], bool]:
        """对任务列表做容错归一化"""
        normalized: list[TodoItemDict] = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            status = str(item.get("status", "pending"))
            if status not in self.VALID_STATUSES:
                status = "pending"
            normalized.append(TodoItemDict(
                id=str(item.get("id", str(i + 1))),
                text=text,
                status=status,
            ))

        truncated = False
        if len(normalized) > self.MAX_ITEMS:
            normalized = normalized[: self.MAX_ITEMS]
            truncated = True

        # 保证仅有一个 in_progress
        seen_in_progress = False
        for item in normalized:
            if item["status"] != "in_progress":
                continue
            if not seen_in_progress:
                seen_in_progress = True
            else:
                item["status"] = "pending"

        return normalized, truncated

    def get_state(self, dialog_id: str) -> TodoState:
        """获取或创建对话的 Todo 状态"""
        with self._lock:
            if dialog_id not in self._states:
                self._states[dialog_id] = TodoState(dialog_id=dialog_id)
            return self._states[dialog_id]

    def update_todos(
        self, dialog_id: str, items: list[dict[str, Any]]
    ) -> tuple[bool, str]:
        """
        更新对话的任务列表

        Args:
            dialog_id: 对话 ID
            items: 任务项列表

        Returns:
            (success, message)
        """
        # 归一化
        normalized_items, truncated = self._normalize_items(items)

        # 校验
        valid, error = self._validate_items(normalized_items)
        if not valid:
            logger.warning(f"[TodoStore] Validation failed for {dialog_id}: {error}")
            return False, error

        # 更新状态
        with self._lock:
            state = self.get_state(dialog_id)
            state.items = [TodoItem.from_dict(item) for item in normalized_items]
            state.used_todo_in_round = True
            state.rounds_since_todo = 0
            state.updated_at = time.time()

        # 广播更新事件
        self._emit(
            dataclasses.asdict(TodoUpdatedEvent(
                dialog_id=dialog_id,
                todos=[item.to_dict() for item in state.items],
                rounds_since_todo=state.rounds_since_todo,
                timestamp=time.time(),
            ))
        )

        logger.debug(f"[TodoStore] Updated {len(items)} todos for {dialog_id}")
        if truncated:
            return True, f"Truncated to {self.MAX_ITEMS} items"
        return True, ""

    def mark_todo_used(self, dialog_id: str) -> None:
        """标记本轮使用了 todo 工具"""
        with self._lock:
            state = self.get_state(dialog_id)
            state.used_todo_in_round = True
            state.rounds_since_todo = 0
            state.updated_at = time.time()

    def after_round(self, dialog_id: str) -> bool:
        """
        轮次结束后更新状态

        Returns:
            是否需要发送 reminder
        """
        with self._lock:
            state = self.get_state(dialog_id)

            if state.used_todo_in_round:
                state.rounds_since_todo = 0
                state.used_todo_in_round = False
                need_reminder = False
            else:
                state.rounds_since_todo += 1
                need_reminder = (
                    state.rounds_since_todo >= self.TODO_REMINDER_ROUNDS
                    and len(state.items) > 0
                    and any(item.status != "completed" for item in state.items)
                )

            state.updated_at = time.time()

        if need_reminder:
            self._emit_reminder(dialog_id, state.rounds_since_todo)

        return need_reminder

    def _emit_reminder(self, dialog_id: str, rounds_since_todo: int) -> None:
        """发送 reminder 事件"""
        self._emit(
            dataclasses.asdict(TodoReminderEvent(
                dialog_id=dialog_id,
                rounds_since_todo=rounds_since_todo,
                timestamp=time.time(),
            ))
        )
        logger.debug(f"[TodoStore] Sent reminder for {dialog_id}")

    def get_todos(self, dialog_id: str) -> TodoStateDTO:
        """获取对话的任务列表"""
        state = self.get_state(dialog_id)
        return TodoStateDTO(
            dialog_id=dialog_id,
            items=[item.to_dict() for item in state.items],
            rounds_since_todo=state.rounds_since_todo,
            updated_at=state.updated_at,
        )

    def clear_dialog(self, dialog_id: str) -> None:
        """清理对话的 Todo 状态"""
        with self._lock:
            if dialog_id in self._states:
                del self._states[dialog_id]


# 全局单例
todo_store = TodoStore()


def is_todo_hook_enabled() -> bool:
    """检查是否启用 Todo Hook"""
    raw = os.getenv("ENABLE_TODO_HOOK", "1")
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}
