"""AgentPlugin - Abstract base class for agent plugins (Builder pattern).

This module provides the plugin interface for the AgentBuilder pattern.
It is independent from the lifecycle hook-based plugin system to avoid circular imports.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..agent.base_agent_loop import BaseAgentLoop


class AgentPlugin(ABC):
    """Abstract base class for agent plugins (Builder pattern).

    Plugins provide modular functionality that can be added to agents via AgentBuilder.
    Each plugin defines its name, tools, and lifecycle hooks.

    This is independent from the lifecycle hook-based plugin system.

    Example:
        class MyPlugin(AgentPlugin):
            @property
            def name(self) -> str:
                return "my_plugin"

            def get_tools(self) -> list[Callable]:
                return [my_tool_function]

            def on_load(self, agent: BaseAgentLoop) -> None:
                # Initialize plugin resources
                pass
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of this plugin.

        Returns:
            String identifier for the plugin.
        """
        ...

    @abstractmethod
    def get_tools(self) -> list[Callable]:
        """Return the list of tool functions provided by this plugin.

        Returns:
            List of callable functions decorated with @tool.
        """
        ...

    def on_load(self, agent: "BaseAgentLoop") -> None:
        """Called when the plugin is loaded into an agent.

        Override this method to initialize plugin resources or
        register event handlers.

        Args:
            agent: The agent instance this plugin is being loaded into.
        """
        # Store reference for later use
        self._builder_agent = agent

    def on_unload(self) -> None:
        """Called when the plugin is unloaded from an agent.

        Override this method to clean up resources or
        unregister event handlers.
        """
        pass
