"""TeamAgent - Agent with team collaboration capabilities."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..plugins.team import TeamPlugin
from ..agent.s_full import TEAM_DIR, INBOX_DIR
from .subagent import SubagentAgent

if TYPE_CHECKING:
    pass


class TeamAgent(SubagentAgent):
    """Agent with team collaboration capabilities.

    Extends SubagentAgent with teammate management and messaging.
    Useful for coordinating work across multiple agents.

    Tools: bash, read_file, write_file, edit_file, todo, subagent,
           spawn_teammate, list_teammates, teammate_idle, claim_work,
           send_msg, broadcast, read_inbox
    """

    def __init__(
        self,
        provider=None,
        model: str = None,
        system: str = None,
        team_dir: Path = None,
        inbox_dir: Path = None,
        **kwargs
    ):
        """Initialize TeamAgent.

        Args:
            provider: LLM provider instance.
            model: Model name to use.
            system: Custom system prompt.
            team_dir: Directory for team data.
            inbox_dir: Directory for message inbox.
            **kwargs: Additional arguments passed to SubagentAgent.
        """
        if system is None:
            system = self._default_system_prompt()

        if team_dir is None:
            team_dir = TEAM_DIR
        if inbox_dir is None:
            inbox_dir = INBOX_DIR

        super().__init__(
            provider=provider,
            model=model,
            system=system,
            **kwargs
        )

        # Add team plugin
        self._team_plugin = TeamPlugin(team_dir=team_dir, inbox_dir=inbox_dir)
        self._team_plugin.on_load(self)

        # Extend tools with team tools
        self.tools.extend(self._team_plugin.get_tools())

    def _default_system_prompt(self) -> str:
        """Return the default system prompt for TeamAgent."""
        return """You are a helpful coding assistant with team collaboration capabilities.

You have access to these tools:
- bash: Run shell commands
- read_file: Read file contents
- write_file: Write files
- edit_file: Edit files
- todo: Manage todo items for multi-step tasks
- subagent: Spawn subagents for task decomposition
- spawn_teammate: Create a new teammate agent
- list_teammates: List all teammates
- teammate_idle: Mark a teammate as idle
- claim_work: Claim work for a teammate
- send_msg: Send a message to a teammate
- broadcast: Send a message to all teammates
- read_inbox: Read messages from inbox

Use teammates to parallelize work:
1. Spawn teammates with specific roles
2. Claim work for idle teammates
3. Communicate via messages for coordination
4. Check inbox regularly for updates"""


# Convenience function
def create_team_agent(**kwargs) -> TeamAgent:
    """Create a TeamAgent instance.

    Args:
        **kwargs: Arguments passed to TeamAgent.

    Returns:
        Configured TeamAgent instance.
    """
    return TeamAgent(**kwargs)
