"""SubagentAgent - Agent with subagent decomposition capabilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..plugins.subagent import SubagentPlugin
from .todo import TodoAgent

if TYPE_CHECKING:
    pass


class SubagentAgent(TodoAgent):
    """Agent with subagent decomposition capabilities.

    Extends TodoAgent with ability to spawn subagents for task decomposition.
    Useful for complex tasks that can be broken down into smaller pieces.

    Tools: bash, read_file, write_file, edit_file, todo, subagent
    """

    def __init__(
        self,
        provider=None,
        model: str = None,
        system: str = None,
        **kwargs
    ):
        """Initialize SubagentAgent.

        Args:
            provider: LLM provider instance.
            model: Model name to use.
            system: Custom system prompt.
            **kwargs: Additional arguments passed to TodoAgent.
        """
        if system is None:
            system = self._default_system_prompt()

        super().__init__(
            provider=provider,
            model=model,
            system=system,
            **kwargs
        )

        # Add subagent plugin
        self._subagent_plugin = SubagentPlugin(provider=provider, model=model)
        self._subagent_plugin.on_load(self)

        # Extend tools with subagent tool
        self.tools.extend(self._subagent_plugin.get_tools())

    def _default_system_prompt(self) -> str:
        """Return the default system prompt for SubagentAgent."""
        return """You are a helpful coding assistant with subagent capabilities.

You have access to these tools:
- bash: Run shell commands
- read_file: Read file contents
- write_file: Write files
- edit_file: Edit files
- todo: Manage todo items for multi-step tasks
- subagent: Spawn subagents for task decomposition

Use the todo tool to track your progress on complex tasks.
Use the subagent tool to delegate tasks that can be worked on independently.
Subagents have limited tools (bash, read_file, write_file, edit_file).

Best practices for subagents:
1. Break complex tasks into clear, independent subtasks
2. Provide detailed prompts to subagents
3. Use agent_type "Explore" for research, "Code" for implementation"""


# Convenience function
def create_subagent_agent(**kwargs) -> SubagentAgent:
    """Create a SubagentAgent instance.

    Args:
        **kwargs: Arguments passed to SubagentAgent.

    Returns:
        Configured SubagentAgent instance.
    """
    return SubagentAgent(**kwargs)
