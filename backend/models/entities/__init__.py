"""
Entity Models - 业务实体模型

按领域拆分的实体模块：
- artifact: 产物实体
- skill: 技能实体
- tool_call: 工具调用实体
- dialog: 对话实体
- message: 消息实体
"""

# 产物和技能
from .artifact import Artifact
from .skill import Skill, SkillDefinition

# 工具调用
from .tool_call import ToolCall, ToolCallOutput

# 对话和消息
from .dialog import Dialog, DialogOutput
from .message import Message

__all__ = [
    # 产物和技能
    "Artifact",
    "Skill",
    "SkillDefinition",
    # 工具调用
    "ToolCall",
    "ToolCallOutput",
    # 对话相关
    "Dialog",
    "Message",
    "DialogOutput",
]
