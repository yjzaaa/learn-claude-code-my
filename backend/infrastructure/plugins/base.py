"""
Plugin Base - 插件基类

定义插件接口和插件管理器。
与 EventBus 集成，无需直接继承 AgentLifecycleHooks。
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from backend.infrastructure.runtime.event_bus import EventBus
from backend.domain.models.events.base import (
    MessageReceived, StreamDelta, MessageCompleted,
    ToolCallStarted, ToolCallCompleted, ErrorOccurred
)


class AgentPlugin(ABC):
    """
    Agent 插件基类

    插件通过订阅 EventBus 事件来响应 Agent 生命周期。
    """

    name: str = "base_plugin"
    description: str = "Base plugin"
    enabled: bool = True

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._event_bus = event_bus
        self._unsubscribe_tokens: List[Callable] = []

    def subscribe(self, callback: Callable, event_types: Optional[List[str]] = None):
        """订阅事件"""
        if self._event_bus:
            unsub = self._event_bus.subscribe(callback, event_types)
            self._unsubscribe_tokens.append(unsub)

    def unsubscribe_all(self):
        """取消所有订阅"""
        for unsub in self._unsubscribe_tokens:
            unsub()
        self._unsubscribe_tokens.clear()

    @abstractmethod
    def activate(self) -> None:
        """
        激活插件

        在此方法中订阅事件。
        """
        raise NotImplementedError

    def deactivate(self) -> None:
        """停用插件"""
        self.unsubscribe_all()

    def get_additional_tools(self) -> List[Callable]:
        """获取插件提供的额外工具"""
        return []

    def get_system_prompt_addon(self) -> str:
        """获取系统提示词追加内容"""
        return ""


class PluginManager:
    """
    插件管理器

    管理多个插件的生命周期。
    """

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._plugins: List[AgentPlugin] = []

    def register(self, plugin_class: type[AgentPlugin]) -> AgentPlugin:
        """
        注册插件

        Args:
            plugin_class: 插件类

        Returns:
            插件实例
        """
        plugin = plugin_class(self._event_bus)
        if plugin.enabled:
            self._plugins.append(plugin)
            plugin.activate()
            print(f"[PluginManager] Registered plugin: {plugin.name}")
        return plugin

    def register_multiple(self, plugin_classes: List[type[AgentPlugin]]) -> None:
        """批量注册插件"""
        for cls in plugin_classes:
            self.register(cls)

    def unregister(self, plugin: AgentPlugin) -> None:
        """注销插件"""
        plugin.deactivate()
        if plugin in self._plugins:
            self._plugins.remove(plugin)

    def clear(self) -> None:
        """清除所有插件"""
        for plugin in self._plugins:
            plugin.deactivate()
        self._plugins.clear()

    def get_all_tools(self) -> List[Callable]:
        """获取所有插件提供的工具"""
        tools = []
        for plugin in self._plugins:
            try:
                tools.extend(plugin.get_additional_tools())
            except Exception as e:
                print(f"[PluginManager] Error getting tools from {plugin.name}: {e}")
        return tools

    def get_combined_system_prompt(self) -> str:
        """获取组合的系统提示词追加内容"""
        parts = []
        for plugin in self._plugins:
            try:
                addon = plugin.get_system_prompt_addon()
                if addon:
                    parts.append(f"\n## {plugin.description}\n{addon}")
            except Exception as e:
                print(f"[PluginManager] Error getting prompt from {plugin.name}: {e}")
        return "\n".join(parts)

    @property
    def plugins(self) -> List[AgentPlugin]:
        """获取所有插件"""
        return self._plugins.copy()
