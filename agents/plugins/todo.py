"""Todo Plugin - Todo management for agents."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from ..base import tool
from .base import AgentPlugin

if TYPE_CHECKING:
    from ..agent.base_agent_loop import BaseAgentLoop


class TodoPlugin(AgentPlugin):
    """Plugin providing todo management functionality.

    Allows agents to track multi-step tasks with pending/in_progress/completed states.
    Integrates with the global todo_store for persistence and event broadcasting.
    """

    @property
    def name(self) -> str:
        return "todo"

    def get_tools(self) -> list[Callable]:
        return [self._todo_tool]

    def on_load(self, agent: "BaseAgentLoop") -> None:
        """Called when plugin is loaded into agent."""
        super().on_load(agent)

    @tool(
        name="todo",
        description="""Manage todo items. Examples:
- {"items": [{"id": "1", "text": "Task", "status": "in_progress"}]}
- {"items": []} to clear all
Valid statuses: pending, in_progress, completed""",
    )
    def _todo_tool(self, items: list[dict[str, Any]]) -> str:
        """Manage todo items for tracking multi-step tasks.

        Args:
            items: List of todo items with id, text, and status.

        Returns:
            JSON response indicating success or failure.
        """
        from ..session.todo_hitl import todo_store
        from ..session.runtime_context import get_current_dialog_id
        from ..models.responses import TodoUpdateResponse

        dialog_id = get_current_dialog_id()
        if not dialog_id:
            return TodoUpdateResponse(
                success=False, error="No active dialog"
            ).model_dump_json()

        success, error = todo_store.update_todos(dialog_id, items)
        if success:
            return TodoUpdateResponse(
                success=True,
                dialog_id=dialog_id,
                item_count=len(items),
                items=items,
            ).model_dump_json()
        else:
            return TodoUpdateResponse(success=False, error=error).model_dump_json()
