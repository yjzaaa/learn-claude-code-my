"""
Plugins - 插件系统

Agent 插件机制，支持上下文压缩等扩展功能。
"""

from backend.infrastructure.plugins.base import AgentPlugin, PluginManager
from backend.infrastructure.plugins.compact_plugin import CompactPlugin

__all__ = ["AgentPlugin", "PluginManager", "CompactPlugin"]
