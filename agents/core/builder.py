"""AgentBuilder - Fluent API for assembling agents with selected plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ..plugins.base import AgentPlugin


class AgentBuilder:
    """Fluent API for assembling agents with selected plugins.

    Example:
        agent = (
            AgentBuilder()
            .with_base_tools()
            .with_plugin(TodoPlugin())
            .with_monitoring(dialog_id="dlg-123")
            .build()
        )
    """

    def __init__(self):
        self._plugins: list[AgentPlugin] = []
        self._plugin_names: set[str] = set()
        self._base_tools_added = False
        self._monitoring_dialog_id: Optional[str] = None
        self._system_prompt: Optional[str] = None
        self._system_append: Optional[str] = None

    # ============ Fluent API Methods ============

    def with_base_tools(self) -> AgentBuilder:
        """Add base tools (bash, read_file, write_file, edit_file).

        Returns:
            Self for method chaining.
        """
        self._base_tools_added = True
        return self

    def with_plugin(self, plugin: AgentPlugin) -> AgentBuilder:
        """Add a plugin to the agent.

        Args:
            plugin: An instance of AgentPlugin.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        plugin_name = plugin.name
        if plugin_name in self._plugin_names:
            raise ValueError(f"Plugin '{plugin_name}' already registered")

        self._plugins.append(plugin)
        self._plugin_names.add(plugin_name)
        return self

    def with_monitoring(self, dialog_id: str) -> AgentBuilder:
        """Enable monitoring with the specified dialog ID.

        Args:
            dialog_id: The dialog ID for monitoring events.

        Returns:
            Self for method chaining.
        """
        self._monitoring_dialog_id = dialog_id
        return self

    def with_system(self, prompt: str) -> AgentBuilder:
        """Set the system prompt.

        Args:
            prompt: The system prompt text.

        Returns:
            Self for method chaining.
        """
        self._system_prompt = prompt
        return self

    def with_system_append(self, text: str) -> AgentBuilder:
        """Append text to the system prompt.

        Args:
            text: Text to append to the system prompt.

        Returns:
            Self for method chaining.
        """
        if self._system_append:
            self._system_append += "\n" + text
        else:
            self._system_append = text
        return self

    # ============ Predefined Builders ============

    @classmethod
    def simple_agent(cls) -> AgentBuilder:
        """Create a builder preconfigured with base tools only.

        Returns:
            AgentBuilder with base tools configured.
        """
        return cls().with_base_tools()

    @classmethod
    def todo_agent(cls) -> AgentBuilder:
        """Create a builder preconfigured with base tools + TodoPlugin.

        Returns:
            AgentBuilder with base tools and TodoPlugin configured.
        """
        from ..plugins.todo import TodoPlugin

        return cls().with_base_tools().with_plugin(TodoPlugin())

    @classmethod
    def full_agent(cls) -> AgentBuilder:
        """Create a builder preconfigured with all plugins.

        Returns:
            AgentBuilder with all plugins configured.
        """
        from ..plugins.todo import TodoPlugin
        from ..plugins.task import TaskPlugin
        from ..plugins.background import BackgroundPlugin
        from ..plugins.subagent import SubagentPlugin
        from ..plugins.team import TeamPlugin
        from ..plugins.plan import PlanPlugin

        return (
            cls()
            .with_base_tools()
            .with_plugin(TodoPlugin())
            .with_plugin(TaskPlugin())
            .with_plugin(BackgroundPlugin())
            .with_plugin(SubagentPlugin())
            .with_plugin(TeamPlugin())
            .with_plugin(PlanPlugin())
        )

    # ============ Build Method ============

    def build(self) -> "BaseAgentLoop":
        """Build and return the configured agent.

        Returns:
            Configured agent instance.

        Raises:
            ValueError: If no tools are registered.
        """
        from ..agent.s_full import SFullAgent

        # Collect all tools from plugins
        tool_registry: dict[str, Callable] = {}

        # Add base tools if requested
        if self._base_tools_added:
            base_tools = self._get_base_tools()
            for tool in base_tools:
                tool_registry[tool.__tool_spec__["name"]] = tool

        # Add plugin tools (later plugins override earlier ones)
        for plugin in self._plugins:
            for tool in plugin.get_tools():
                tool_registry[tool.__tool_spec__["name"]] = tool

        # Validate: must have at least one tool
        if not tool_registry:
            raise ValueError("Agent must have at least one tool")

        # Build system prompt
        system_prompt = self._build_system_prompt()

        # Create agent
        agent = SFullAgent(
            tools=list(tool_registry.values()),
            system_prompt=system_prompt,
        )

        # Set up monitoring if requested
        if self._monitoring_dialog_id:
            from ..monitoring.bridge.composite import CompositeMonitoringBridge
            from ..hooks.state_managed_agent_bridge import StateManagedAgentBridge

            bridge = CompositeMonitoringBridge(self._monitoring_dialog_id)
            agent._monitoring_bridge = bridge

        # Initialize plugins
        for plugin in self._plugins:
            plugin.on_load(agent)

        return agent

    # ============ Private Helpers ============

    def _get_base_tools(self) -> list[Callable]:
        """Get the base tool functions."""
        from ..tools.basetool import run_bash, read_file, write_file, edit_file

        return [run_bash, read_file, write_file, edit_file]

    def _build_system_prompt(self) -> str:
        """Build the final system prompt."""
        if self._system_prompt:
            base_prompt = self._system_prompt
        else:
            base_prompt = self._get_default_system_prompt()

        if self._system_append:
            return base_prompt + "\n" + self._system_append

        return base_prompt

    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt."""
        return (
            "You are a helpful AI assistant with access to tools. "
            "Use the available tools to complete tasks efficiently."
        )