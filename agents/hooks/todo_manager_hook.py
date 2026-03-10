"""TodoManager Hook：管理任务列表状态，支持提醒和状态同步。"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

try:
    from ..base.abstract import FullAgentHooks
    from ..session.todo_hitl import TodoStore
except ImportError:
    from agents.base.abstract import FullAgentHooks
    from agents.session.todo_hitl import TodoStore


class TodoManagerHook(FullAgentHooks):
    """
    管理对话中的任务列表状态。

    - on_before_run: 检查是否需要插入 reminder
    - on_tool_result: 识别 todo 工具调用并更新状态
    - on_after_run: 维护 rounds_since_todo 计数
    - on_stop: 清理轮次临时状态
    """

    TODO_TOOL_NAMES = {"todo", "manage_todo_list"}

    def __init__(self, dialog_id: str, store: TodoStore):
        self.dialog_id = dialog_id
        self.store = store
        self._used_todo_this_round = False
        self._reminder_inserted = False

    def on_before_run(self, messages: list[dict[str, Any]]) -> None:
        """
        在 Agent 运行前检查是否需要插入 reminder。

        当 rounds_since_todo >= TODO_REMINDER_ROUNDS 时，
        在最后一条用户消息后插入 reminder。
        """
        state = self.store.get_state(self.dialog_id)

        # 检查是否需要提醒
        if state.rounds_since_todo < self.store.TODO_REMINDER_ROUNDS:
            return

        # 检查是否还有待完成的任务
        has_pending = any(
            item.status != "completed" for item in state.items
        )
        if not has_pending:
            return

        # 查找最后一条用户消息的位置
        last_user_idx = -1
        for i, msg in enumerate(messages):
            role = msg.get("role", "")
            if role in {"user", "Role.USER"}:
                last_user_idx = i

        if last_user_idx == -1:
            return

        # 在最后一条用户消息后插入 reminder
        reminder_msg = {
            "role": "system",
            "content": "<reminder>Update your todos.</reminder>",
        }

        # 避免重复插入
        if not self._reminder_inserted:
            messages.insert(last_user_idx + 1, reminder_msg)
            self._reminder_inserted = True
            logger.debug(
                f"[TodoManagerHook] Inserted reminder for {self.dialog_id}"
            )

    def on_stream_token(self, chunk: Any) -> None:
        """忽略流式 token。"""
        _ = chunk

    def on_tool_call(
        self, name: str, arguments: dict[str, Any], tool_call_id: str = ""
    ) -> None:
        """忽略工具调用开始。"""
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
        """
        识别 todo 工具调用结果并更新状态。

        支持的工具名：todo, manage_todo_list
        """
        _ = assistant_message
        _ = tool_call_id

        if name not in self.TODO_TOOL_NAMES:
            return

        logger.debug(
            f"[TodoManagerHook] Detected todo tool call: {name}"
        )

        # 尝试解析结果为 JSON
        items = self._parse_todo_result(result)

        if items is not None:
            # 成功解析，更新状态
            success, error = self.store.update_todos(self.dialog_id, items)
            if success:
                self._used_todo_this_round = True
                logger.debug(
                    f"[TodoManagerHook] Updated {len(items)} todos for {self.dialog_id}"
                )
            else:
                logger.warning(
                    f"[TodoManagerHook] Failed to update todos: {error}"
                )
        else:
            # 解析失败，但至少标记使用了 todo
            self.store.mark_todo_used(self.dialog_id)
            self._used_todo_this_round = True
            logger.debug(
                f"[TodoManagerHook] Marked todo used (unparseable result) for {self.dialog_id}"
            )

    def _parse_todo_result(self, result: str) -> list[dict[str, Any]] | None:
        """
        解析工具结果为任务列表。

        支持格式：
        - JSON 数组: [{"id": "1", "text": "...", "status": "pending"}]
        - JSON 对象: {"items": [...]}

        Returns:
            解析成功返回 items 列表，失败返回 None
        """
        if not result or not result.strip():
            return None

        try:
            data = json.loads(result)

            # 如果是数组，直接使用
            if isinstance(data, list):
                return data

            # 如果是对象，尝试获取 items 字段
            if isinstance(data, dict):
                if "items" in data:
                    items = data["items"]
                    if isinstance(items, list):
                        return items

            # 尝试其他常见字段名
            for key in ["todos", "tasks", "data"]:
                if key in data and isinstance(data[key], list):
                    return data[key]

            logger.warning(
                f"[TodoManagerHook] Could not find items in result: {result[:200]}"
            )
            return None

        except json.JSONDecodeError:
            logger.warning(
                f"[TodoManagerHook] Failed to parse result as JSON: {result[:200]}"
            )
            return None
        except Exception as e:
            logger.warning(
                f"[TodoManagerHook] Error parsing result: {e}"
            )
            return None

    def on_complete(self, content: str) -> None:
        """忽略消息完成。"""
        _ = content

    def on_error(self, error: Exception) -> None:
        """忽略错误。"""
        _ = error

    def on_after_run(self, messages: list[dict[str, Any]], rounds: int) -> None:
        """
        轮次结束后更新状态。

        - 如果本轮使用了 todo 工具：rounds_since_todo = 0
        - 否则：rounds_since_todo += 1
        """
        _ = messages
        _ = rounds

        # 如果有显式标记，优先使用
        if self._used_todo_this_round:
            state = self.store.get_state(self.dialog_id)
            state.rounds_since_todo = 0
            state.used_todo_in_round = False
            self._used_todo_this_round = False
            return

        # 否则调用 store 的 after_round 来维护计数
        self.store.after_round(self.dialog_id)

    def on_stop(self) -> None:
        """清理轮次临时状态。"""
        self._used_todo_this_round = False
        self._reminder_inserted = False
