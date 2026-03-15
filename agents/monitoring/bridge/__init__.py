"""
Monitoring Bridge Module

监控桥接器模块，提供 Agent 与监控系统之间的桥接功能。
"""

from __future__ import annotations

# 从 base.py 导入基础桥接器
from .base import (
    IMonitoringBridge,
    BaseMonitoringBridge,
)

# 从 composite.py 导入组合桥接器
from .composite import (
    ChildMonitoringBridge,
    BackgroundTaskBridge,
    CompositeMonitoringBridge,
)

__all__ = [
    "IMonitoringBridge",
    "BaseMonitoringBridge",
    "ChildMonitoringBridge",
    "BackgroundTaskBridge",
    "CompositeMonitoringBridge",
]
