"""Background Plugin - Background task execution for agents."""

from __future__ import annotations

import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from ..base import tool
from .base import AgentPlugin

if TYPE_CHECKING:
    from ..agent.base_agent_loop import BaseAgentLoop


class BackgroundManager:
    """Manage background task execution."""

    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: dict[str, dict] = {}

    def run(self, command: str, timeout: int = 300) -> str:
        """Start a background command."""
        task_id = f"bg_{int(time.time() * 1000)}"
        self.tasks[task_id] = {
            "id": task_id,
            "command": command,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "result": None,
        }

        def execute():
            try:
                r = subprocess.run(
                    command, shell=True,
                    capture_output=True, text=True, timeout=timeout
                )
                self.tasks[task_id]["status"] = "completed"
                self.tasks[task_id]["result"] = (r.stdout + r.stderr).strip()[:50000]
                self.tasks[task_id]["completed_at"] = datetime.now().isoformat()
            except subprocess.TimeoutExpired:
                self.tasks[task_id]["status"] = "timeout"
                self.tasks[task_id]["result"] = f"Timeout ({timeout}s)"
            except Exception as e:
                self.tasks[task_id]["status"] = "error"
                self.tasks[task_id]["result"] = str(e)

        self.tasks[task_id]["future"] = self.executor.submit(execute)
        return task_id

    def check(self, task_id: str) -> dict:
        """Check background task status."""
        task = self.tasks.get(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}
        return {
            "id": task["id"],
            "status": task["status"],
            "command": task["command"],
            "result": task.get("result"),
            "started_at": task.get("started_at"),
            "completed_at": task.get("completed_at"),
        }


class BackgroundPlugin(AgentPlugin):
    """Plugin providing background task execution.

    Allows agents to run commands asynchronously and check their status later.
    Emits monitoring events for task lifecycle (BG_TASK_*).
    """

    def __init__(self, max_workers: int = 4):
        super().__init__()
        self._manager = BackgroundManager(max_workers=max_workers)

    @property
    def name(self) -> str:
        return "background"

    def get_tools(self) -> list[Callable]:
        return [
            self._bg_run,
            self._bg_check,
        ]

    @tool(
        name="bg_run",
        description="Run a command in the background. Returns task_id immediately."
    )
    def _bg_run(self, command: str, timeout: int = 300) -> str:
        """Start a background command.

        Args:
            command: Shell command to execute.
            timeout: Maximum execution time in seconds.

        Returns:
            JSON with task_id and status.
        """
        try:
            from ..session.runtime_context import get_current_monitoring_bridge

            bridge = get_current_monitoring_bridge()
            if bridge and hasattr(bridge, 'create_background_task_bridge'):
                # Use monitoring-aware background execution
                import asyncio
                task_id = f"bg_{int(time.time() * 1000)}"
                bg_bridge = bridge.create_background_task_bridge(task_id, command)
                # Start the process asynchronously
                asyncio.create_task(bg_bridge.start_process())
                return json.dumps({
                    "task_id": bg_bridge.task_id,
                    "status": "queued"
                })
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to use monitoring bridge: {e}")

        # Fallback to simple execution
        task_id = self._manager.run(command, timeout)
        return json.dumps({"task_id": task_id, "status": "running"})

    @tool(
        name="bg_check",
        description="Check status of a background task."
    )
    def _bg_check(self, task_id: str) -> str:
        """Check background task status.

        Args:
            task_id: The task ID returned by bg_run.

        Returns:
            JSON with task status and result if completed.
        """
        # First try to check via monitoring bridge
        try:
            from ..session.runtime_context import get_current_monitoring_bridge

            bridge = get_current_monitoring_bridge()
            if bridge and hasattr(bridge, 'get_background_task_bridges'):
                for bg_bridge in bridge.get_background_task_bridges():
                    if bg_bridge.task_id == task_id:
                        return json.dumps({
                            "id": task_id,
                            "status": bg_bridge.task_status,
                            "command": bg_bridge.command,
                            "result": bg_bridge.get_output() if bg_bridge.task_status in ("completed", "failed") else None,
                            "exit_code": bg_bridge.exit_code,
                        }, ensure_ascii=False)
        except Exception:
            pass

        # Fallback to local manager
        result = self._manager.check(task_id)
        return json.dumps(result, ensure_ascii=False)
