#!/usr/bin/env python3
"""
Agent 插件系统

允许以插件形式扩展 TeamLeadAgent 功能，支持：
- 技能加载 (SkillPlugin)
- 上下文压缩 (CompactPlugin)

插件生命周期：
1. __init__(agent) - 插件初始化
2. on_before_run(messages) - 运行前处理
3. on_stream_token(chunk) - 流式 token 处理
4. on_tool_call(name, arguments) - 工具调用处理
5. on_tool_result(name, result) - 工具结果处理
6. on_complete(content) - 完成处理
7. on_error(error) - 错误处理
8. get_additional_tools() - 获取额外工具
9. get_system_prompt_addon() - 获取系统提示词追加内容
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Protocol


class AgentPlugin(ABC):
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

    def on_before_run(self, messages: List[Dict]) -> None:
        """
        在 Agent 运行前调用

        Args:
            messages: 消息列表（可原地修改）
        """
        pass

    def on_stream_token(self, chunk: Any) -> None:
        """
        收到流式 token 时调用

        Args:
            chunk: 内容块
        """
        pass

    def on_tool_call(self, name: str, arguments: Dict) -> None:
        """
        工具调用时调用

        Args:
            name: 工具名称
            arguments: 工具参数
        """
        pass

    def on_tool_result(self, name: str, result: str) -> None:
        """
        收到工具结果时调用

        Args:
            name: 工具名称
            result: 工具返回结果
        """
        pass

    def on_complete(self, content: str) -> None:
        """
        一轮对话完成时调用

        Args:
            content: 完成的文本内容
        """
        pass

    def on_error(self, error: Exception) -> None:
        """
        发生错误时调用

        Args:
            error: 异常对象
        """
        pass

    def on_stop(self) -> None:
        """Agent 停止时调用"""
        pass

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


__all__ = [
    "AgentPlugin",
    "PluginManager",
]