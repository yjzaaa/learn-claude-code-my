"""SimpleAgent - Base agent with only essential tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base.base_agent_loop import BaseAgentLoop
from ..agent.s_full import run_bash, run_read, run_write, run_edit

if TYPE_CHECKING:
    pass


class SimpleAgent(BaseAgentLoop):
    """Simple agent with base tools only.

    This is the base class in the agent hierarchy.
    Provides essential file and command execution tools.

    Tools: bash, read_file, write_file, edit_file
    """

    def __init__(
        self,
        provider=None,
        model: str = None,
        system: str = None,
        **kwargs
    ):
        """Initialize SimpleAgent.

        Args:
            provider: LLM provider instance.
            model: Model name to use.
            system: Custom system prompt.
            **kwargs: Additional arguments passed to BaseAgentLoop.
        """
        if system is None:
            system = self._default_system_prompt()

        # Base tools only
        tools = [run_bash, run_read, run_write, run_edit]

        super().__init__(
            provider=provider,
            model=model,
            system=system,
            tools=tools,
            **kwargs
        )

    def _default_system_prompt(self) -> str:
        """Return the default system prompt for SimpleAgent."""
        return """You are a helpful coding assistant.

You have access to these tools:
- bash: Run shell commands
- read_file: Read file contents
- write_file: Write files
- edit_file: Edit files

Use these tools to help users with their tasks."""


# Convenience function
def create_simple_agent(**kwargs) -> SimpleAgent:
    """Create a SimpleAgent instance.

    Args:
        **kwargs: Arguments passed to SimpleAgent.

    Returns:
        Configured SimpleAgent instance.
    """
    return SimpleAgent(**kwargs)
