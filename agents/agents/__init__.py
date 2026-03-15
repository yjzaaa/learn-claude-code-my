"""Agent Implementations Package

Provides a hierarchy of agent classes with increasing capabilities.

Agent Hierarchy:
    SimpleAgent → TodoAgent → SubagentAgent → TeamAgent → FullAgent

Each level adds capabilities:
- SimpleAgent: Base tools (bash, read_file, write_file, edit_file)
- TodoAgent: + Todo management for session progress tracking
- SubagentAgent: + Subagent spawning for task decomposition
- TeamAgent: + Team collaboration (teammates, messaging)
- FullAgent: + Background tasks, persistent tasks, plan approval

Usage Examples:
    # Use a predefined agent
    from agents.agents import FullAgent
    agent = FullAgent()

    # Use AgentBuilder for custom combinations
    from agents.core import AgentBuilder
    from agents.plugins import TodoPlugin, TaskPlugin

    agent = (
        AgentBuilder()
        .with_base_tools()
        .with_plugin(TodoPlugin())
        .with_plugin(TaskPlugin())
        .with_monitoring(dialog_id="dlg-123")
        .build()
    )

Migration from SFullAgent:
    # Old way (still works, but deprecated)
    from agents.agent.s_full import SFullAgent

    # New way (recommended)
    from agents.agents import FullAgent
    # or
    from agents.agents import create_full_agent
"""

from .simple import SimpleAgent, create_simple_agent
from .todo import TodoAgent, create_todo_agent
from .subagent import SubagentAgent, create_subagent_agent
from .team import TeamAgent, create_team_agent
from .full import FullAgent, SFullAgent, create_full_agent

__all__ = [
    # Agent classes
    "SimpleAgent",
    "TodoAgent",
    "SubagentAgent",
    "TeamAgent",
    "FullAgent",
    # Backward compatibility
    "SFullAgent",
    # Factory functions
    "create_simple_agent",
    "create_todo_agent",
    "create_subagent_agent",
    "create_team_agent",
    "create_full_agent",
]
