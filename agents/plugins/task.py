"""Task Plugin - Persistent task management for agents."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from ..base import tool
from .base import AgentPlugin

if TYPE_CHECKING:
    from ..agent.base_agent_loop import BaseAgentLoop


class TaskManager:
    """Persistent task management."""

    def __init__(self, tasks_dir: Path):
        self.tasks_dir = tasks_dir
        self.tasks_dir.mkdir(exist_ok=True)

    def _task_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.json"

    def create(self, title: str, description: str = "", assignee: str = "") -> dict:
        """Create a new task."""
        task_id = f"task_{int(time.time() * 1000)}"
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "status": "open",
            "assignee": assignee,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._task_path(task_id).write_text(json.dumps(task, indent=2), encoding="utf-8")
        return task

    def get(self, task_id: str) -> dict | None:
        """Get task by ID."""
        path = self._task_path(task_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def update(self, task_id: str, **updates) -> dict | None:
        """Update task fields."""
        task = self.get(task_id)
        if not task:
            return None
        task.update(updates)
        task["updated_at"] = datetime.now().isoformat()
        self._task_path(task_id).write_text(json.dumps(task, indent=2), encoding="utf-8")
        return task

    def list(self, status: str = None) -> list[dict]:
        """List all tasks, optionally filtered by status."""
        tasks = []
        for f in self.tasks_dir.glob("*.json"):
            try:
                task = json.loads(f.read_text(encoding="utf-8"))
                if status is None or task.get("status") == status:
                    tasks.append(task)
            except Exception:
                continue
        return sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True)


class TaskPlugin(AgentPlugin):
    """Plugin providing persistent task management.

    Tasks are stored as JSON files for persistence across sessions.
    """

    def __init__(self, tasks_dir: Path | None = None):
        super().__init__()
        if tasks_dir is None:
            from ..agent.s_full import TASKS_DIR
            tasks_dir = TASKS_DIR
        self._manager = TaskManager(tasks_dir)

    @property
    def name(self) -> str:
        return "task"

    def get_tools(self) -> list[Callable]:
        return [
            self._task_create,
            self._task_get,
            self._task_update,
            self._task_list,
        ]

    @tool(
        name="task_create",
        description="Create a new persistent task."
    )
    def _task_create(self, title: str, description: str = "") -> str:
        """Create a new task."""
        task = self._manager.create(title, description)
        return json.dumps(task, ensure_ascii=False)

    @tool(
        name="task_get",
        description="Get a task by ID."
    )
    def _task_get(self, task_id: str) -> str:
        """Get task by ID."""
        task = self._manager.get(task_id)
        if task:
            return json.dumps(task, ensure_ascii=False)
        return json.dumps({"error": f"Task {task_id} not found"})

    @tool(
        name="task_update",
        description="Update a task's status or other fields."
    )
    def _task_update(self, task_id: str, status: str = None, title: str = None, description: str = None) -> str:
        """Update task fields."""
        updates = {}
        if status:
            updates["status"] = status
        if title:
            updates["title"] = title
        if description:
            updates["description"] = description
        task = self._manager.update(task_id, **updates)
        if task:
            return json.dumps(task, ensure_ascii=False)
        return json.dumps({"error": f"Task {task_id} not found"})

    @tool(
        name="task_list",
        description="List tasks, optionally filtered by status."
    )
    def _task_list(self, status: str = None) -> str:
        """List all tasks."""
        tasks = self._manager.list(status)
        return json.dumps(tasks, ensure_ascii=False)
