#!/usr/bin/env python3
"""
Agent Plugins Package

Provides modular plugins that can be combined to create custom agents.
Each plugin encapsulates a specific functionality domain.

Built-in plugins (Builder pattern):
- TodoPlugin: Todo management for tracking multi-step tasks
- TaskPlugin: Persistent task storage across sessions
- BackgroundPlugin: Background command execution with monitoring
- SubagentPlugin: Subagent spawning for task decomposition
- TeamPlugin: Team collaboration with messaging and work claiming
- PlanPlugin: Plan approval gate for significant changes

Example:
    from agents.plugins import TodoPlugin, TaskPlugin
    from agents.core import AgentBuilder

    agent = (
        AgentBuilder()
        .with_base_tools()
        .with_plugin(TodoPlugin())
        .with_plugin(TaskPlugin())
        .build()
    )

Legacy plugin system (Lifecycle hooks):
- AgentPlugin: Base class for lifecycle hook-based plugins
- PluginManager: Manages multiple lifecycle plugins
"""

from abc import abstractmethod
from typing import Any, Callable, Dict, List

from ..base.abstract import AgentLifecycleHooks, HookName


class AgentPlugin(AgentLifecycleHooks):
    """
    Agent 插件基类

    所有插件必须继承此类并实现相关方法。
    """

    name: str = "base_plugin"
    description: str = "Base plugin"
    enabled: bool = True

    def __init__(self, agent: Any):
        """
        初始化插件

        Args:
            agent: 所属的 Agent 实例
        """
        self.agent = agent

    def on_hook(self, hook: HookName, **payload: Any) -> None:
        """Enum-based hook dispatcher required by AgentLifecycleHooks."""
        if hook == HookName.ON_BEFORE_RUN:
            self.on_before_run(payload.get("messages", []))
        elif hook == HookName.ON_STREAM_TOKEN:
            self.on_stream_token(payload.get("chunk"))
        elif hook == HookName.ON_TOOL_CALL:
            self.on_tool_call(payload.get("name", ""), payload.get("arguments", {}))
        elif hook == HookName.ON_TOOL_RESULT:
            self.on_tool_result(
                payload.get("name", ""),
                payload.get("result", ""),
                payload.get("assistant_message"),
                str(payload.get("tool_call_id", "")),
            )
        elif hook == HookName.ON_COMPLETE:
            self.on_complete(payload.get("content", ""))
        elif hook == HookName.ON_ERROR:
            err = payload.get("error")
            self.on_error(err if isinstance(err, Exception) else Exception(str(err)))
        elif hook == HookName.ON_AFTER_RUN:
            self.on_after_run(payload.get("messages", []), int(payload.get("rounds", 0)))
        elif hook == HookName.ON_STOP:
            self.on_stop()

    @abstractmethod
    def on_before_run(self, messages: List[Dict]) -> None:
        """
        在 Agent 运行前调用

        Args:
            messages: 消息列表（可原地修改）
        """
        raise NotImplementedError

    @abstractmethod
    def on_stream_token(self, chunk: Any) -> None:
        """
        收到流式 token 时调用

        Args:
            chunk: 内容块
        """
        raise NotImplementedError

    @abstractmethod
    def on_tool_call(self, name: str, arguments: Dict) -> None:
        """
        工具调用时调用

        Args:
            name: 工具名称
            arguments: 工具参数
        """
        raise NotImplementedError

    @abstractmethod
    def on_tool_result(
        self,
        name: str,
        result: str,
        assistant_message: Dict[str, Any] | None = None,
        tool_call_id: str = "",
    ) -> None:
        """
        收到工具结果时调用

        Args:
            name: 工具名称
            result: 工具返回结果
            assistant_message: 触发该工具调用的 assistant 消息
            tool_call_id: 工具调用 id
        """
        raise NotImplementedError

    @abstractmethod
    def on_complete(self, content: str) -> None:
        """
        一轮对话完成时调用

        Args:
            content: 完成的文本内容
        """
        raise NotImplementedError

    @abstractmethod
    def on_error(self, error: Exception) -> None:
        """
        发生错误时调用

        Args:
            error: 异常对象
        """
        raise NotImplementedError

    @abstractmethod
    def on_after_run(self, messages: List[Dict], rounds: int) -> None:
        """Agent 运行结束后调用（无论成功/失败）。"""
        raise NotImplementedError

    @abstractmethod
    def on_stop(self) -> None:
        """Agent 停止时调用"""
        raise NotImplementedError

    def get_additional_tools(self) -> List[Callable]:
        """
        获取插件提供的额外工具

        Returns:
            工具函数列表（使用 @tool 装饰器装饰）
        """
        return []

    def get_tool_handlers(self) -> Dict[str, Callable]:
        """
        获取工具处理器映射

        Returns:
            {工具名: 处理器函数} 的字典
        """
        return {}

    def get_system_prompt_addon(self) -> str:
        """
        获取系统提示词追加内容

        Returns:
            要追加到系统提示词的字符串
        """
        return ""


class PluginManager:
    """
    插件管理器

    管理多个插件的生命周期和协调调用。
    """

    def __init__(self, agent: Any):
        self.agent = agent
        self.plugins: List[AgentPlugin] = []

    def register(self, plugin_class: type[AgentPlugin]) -> None:
        """
        注册插件

        Args:
            plugin_class: 插件类（非实例）
        """
        plugin = plugin_class(self.agent)
        if plugin.enabled:
            self.plugins.append(plugin)
            print(f"[PluginManager] Registered plugin: {plugin.name}")

    def register_multiple(self, plugin_classes: List[type[AgentPlugin]]) -> None:
        """批量注册插件"""
        for cls in plugin_classes:
            self.register(cls)

    def on_before_run(self, messages: List[Dict]) -> None:
        """调用所有插件的 on_before_run"""
        for plugin in self.plugins:
            try:
                plugin.on_before_run(messages)
            except Exception as e:
                print(f"[PluginManager] Error in {plugin.name}.on_before_run: {e}")

    def on_stream_token(self, chunk: Any) -> None:
        """调用所有插件的 on_stream_token"""
        for plugin in self.plugins:
            try:
                plugin.on_stream_token(chunk)
            except Exception as e:
                print(f"[PluginManager] Error in {plugin.name}.on_stream_token: {e}")

    def on_tool_call(self, name: str, arguments: Dict) -> None:
        """调用所有插件的 on_tool_call"""
        for plugin in self.plugins:
            try:
                plugin.on_tool_call(name, arguments)
            except Exception as e:
                print(f"[PluginManager] Error in {plugin.name}.on_tool_call: {e}")

    def on_tool_result(self, name: str, result: str) -> None:
        """调用所有插件的 on_tool_result"""
        for plugin in self.plugins:
            try:
                plugin.on_tool_result(name, result)
            except Exception as e:
                print(f"[PluginManager] Error in {plugin.name}.on_tool_result: {e}")

    def on_complete(self, content: str) -> None:
        """调用所有插件的 on_complete"""
        for plugin in self.plugins:
            try:
                plugin.on_complete(content)
            except Exception as e:
                print(f"[PluginManager] Error in {plugin.name}.on_complete: {e}")

    def on_error(self, error: Exception) -> None:
        """调用所有插件的 on_error"""
        for plugin in self.plugins:
            try:
                plugin.on_error(error)
            except Exception as e:
                print(f"[PluginManager] Error in {plugin.name}.on_error: {e}")

    def on_stop(self) -> None:
        """调用所有插件的 on_stop"""
        for plugin in self.plugins:
            try:
                plugin.on_stop()
            except Exception as e:
                print(f"[PluginManager] Error in {plugin.name}.on_stop: {e}")

    def get_all_tools(self) -> List[Callable]:
        """获取所有插件提供的工具"""
        tools = []
        for plugin in self.plugins:
            try:
                tools.extend(plugin.get_additional_tools())
            except Exception as e:
                print(f"[PluginManager] Error getting tools from {plugin.name}: {e}")
        return tools

    def get_all_tool_handlers(self) -> Dict[str, Callable]:
        """获取所有插件提供的工具处理器"""
        handlers = {}
        for plugin in self.plugins:
            try:
                handlers.update(plugin.get_tool_handlers())
            except Exception as e:
                print(f"[PluginManager] Error getting handlers from {plugin.name}: {e}")
        return handlers

    def get_combined_system_prompt(self) -> str:
        """获取组合的系统提示词追加内容"""
        parts = []
        for plugin in self.plugins:
            try:
                addon = plugin.get_system_prompt_addon()
                if addon:
                    parts.append(f"\n## {plugin.description}\n{addon}")
            except Exception as e:
                print(f"[PluginManager] Error getting prompt from {plugin.name}: {e}")
        return "\n".join(parts)


# Export AgentPlugin from base.py (builder pattern)
# This overrides the previous AgentPlugin class with the extended version
from .base import AgentPlugin

# Export specific plugins
from .todo import TodoPlugin
from .task import TaskPlugin
from .background import BackgroundPlugin
from .subagent import SubagentPlugin
from .team import TeamPlugin
from .plan import PlanPlugin

__all__ = [
    "AgentLifecycleHooks",
    "AgentPlugin",
    "PluginManager",
    # Builder pattern plugins
    "TodoPlugin",
    "TaskPlugin",
    "BackgroundPlugin",
    "SubagentPlugin",
    "TeamPlugin",
    "PlanPlugin",
]