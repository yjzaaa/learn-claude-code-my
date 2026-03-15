"""FullAgent - Complete agent with all capabilities."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..plugins.background import BackgroundPlugin
from ..plugins.plan import PlanPlugin
from ..plugins.task import TaskPlugin
from ..agent.s_full import TASKS_DIR
from .team import TeamAgent

if TYPE_CHECKING:
    pass


class FullAgent(TeamAgent):
    """Complete agent with all capabilities.

    Extends TeamAgent with background task execution, persistent tasks,
    and plan approval gating.

    This is the most capable agent class, suitable for complex workflows.

    Tools: All team tools + bg_run, bg_check, task_create, task_get,
           task_update, task_list, submit_plan, review_plan
    """

    def __init__(
        self,
        provider=None,
        model: str = None,
        system: str = None,
        tasks_dir: Path = None,
        max_bg_workers: int = 4,
        **kwargs
    ):
        """Initialize FullAgent.

        Args:
            provider: LLM provider instance.
            model: Model name to use.
            system: Custom system prompt.
            tasks_dir: Directory for persistent task storage.
            max_bg_workers: Maximum concurrent background workers.
            **kwargs: Additional arguments passed to TeamAgent.
        """
        if system is None:
            system = self._default_system_prompt()

        if tasks_dir is None:
            tasks_dir = TASKS_DIR

        super().__init__(
            provider=provider,
            model=model,
            system=system,
            **kwargs
        )

        # Add additional plugins
        self._background_plugin = BackgroundPlugin(max_workers=max_bg_workers)
        self._background_plugin.on_load(self)
        self.tools.extend(self._background_plugin.get_tools())

        self._task_plugin = TaskPlugin(tasks_dir=tasks_dir)
        self._task_plugin.on_load(self)
        self.tools.extend(self._task_plugin.get_tools())

        self._plan_plugin = PlanPlugin()
        self._plan_plugin.on_load(self)
        self.tools.extend(self._plan_plugin.get_tools())

    def _default_system_prompt(self) -> str:
        """Return the default system prompt for FullAgent."""
        return """You are a fully-capable coding assistant.

You have access to these tools:

File & Command Tools:
- bash: Run shell commands
- read_file: Read file contents
- write_file: Write files
- edit_file: Edit files

Task Management:
- todo: Manage in-memory todo items for current session
- task_create, task_get, task_update, task_list: Persistent task storage

Execution:
- subagent: Spawn subagents for task decomposition
- bg_run, bg_check: Run commands in background threads

Team Collaboration:
- spawn_teammate, list_teammates, teammate_idle, claim_work
- send_msg, broadcast, read_inbox

Planning:
- submit_plan, review_plan: Submit plans for approval

Use these tools strategically:
1. Use todos for tracking session progress
2. Use persistent tasks for cross-session work
3. Use background execution for long-running commands
4. Use subagents for independent subtasks
5. Use teammates for parallel work coordination
6. Use plan approval for significant changes"""


# Backward compatibility alias
SFullAgent = FullAgent


# Convenience function
def create_full_agent(**kwargs) -> FullAgent:
    """Create a FullAgent instance.

    Args:
        **kwargs: Arguments passed to FullAgent.

    Returns:
        Configured FullAgent instance.
    """
    return FullAgent(**kwargs)
