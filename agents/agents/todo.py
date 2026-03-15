"""TodoAgent - Agent with todo management capabilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..plugins.todo import TodoPlugin
from .simple import SimpleAgent

if TYPE_CHECKING:
    pass


class TodoAgent(SimpleAgent):
    """Agent with todo management capabilities.

    Extends SimpleAgent with todo tracking functionality.
    Useful for multi-step tasks that need progress tracking.

    Tools: bash, read_file, write_file, edit_file, todo
    """

    def __init__(
        self,
        provider=None,
        model: str = None,
        system: str = None,
        **kwargs
    ):
        """Initialize TodoAgent.

        Args:
            provider: LLM provider instance.
            model: Model name to use.
            system: Custom system prompt.
            **kwargs: Additional arguments passed to SimpleAgent.
        """
        if system is None:
            system = self._default_system_prompt()

        super().__init__(
            provider=provider,
            model=model,
            system=system,
            **kwargs
        )

        # Add todo plugin
        self._todo_plugin = TodoPlugin()
        self._todo_plugin.on_load(self)

        # Extend tools with todo tool
        self.tools.extend(self._todo_plugin.get_tools())

    def _default_system_prompt(self) -> str:
        """Return the default system prompt for TodoAgent."""
        return """You are a helpful coding assistant with todo tracking.

You have access to these tools:
- bash: Run shell commands
- read_file: Read file contents
- write_file: Write files
- edit_file: Edit files
- todo: Manage todo items for multi-step tasks

Use the todo tool to track your progress on complex tasks.
Keep exactly one item "in_progress" at a time.
Update todos as you complete items."""


# Convenience function
def create_todo_agent(**kwargs) -> TodoAgent:
    """Create a TodoAgent instance.

    Args:
        **kwargs: Arguments passed to TodoAgent.

    Returns:
        Configured TodoAgent instance.
    """
    return TodoAgent(**kwargs)
