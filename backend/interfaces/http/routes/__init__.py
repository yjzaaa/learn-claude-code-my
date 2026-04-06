"""
HTTP Routes - API 路由

- health: 健康检查
- dialog: 对话管理
- skills: 技能管理
- tools: 工具管理
- hitl: 人工介入管理
"""

# 新路由模块（基于拆分后的 main.py）
# 原有路由模块
from . import agent, dialog, dialogs, health, hitl, messages, skills, tools

__all__ = [
    # 新路由
    "dialogs",
    "messages",
    "agent",
    # 原有路由
    "health",
    "dialog",
    "skills",
    "tools",
    "hitl",
]
