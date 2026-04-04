"""
Plugins - 插件系统

基于事件驱动的插件架构，与 EventBus 集成。
"""

from .base import AgentPlugin, PluginManager
from .compact_plugin import CompactPlugin

__all__ = [
    "AgentPlugin",
    "PluginManager",
    "CompactPlugin",
]
