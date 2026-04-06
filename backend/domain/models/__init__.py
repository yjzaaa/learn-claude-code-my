"""
Domain Models - 领域模型层

按领域组织的模型定义，包括实体、值对象和领域事件。
"""

# 从 shared 模块重新导出核心类型
from backend.domain.models.agent.skill import Skill, SkillDefinition

# 从 agent 模块导出
from backend.domain.models.agent.tool_call import ToolCall

# 导出 types 模块
from backend.domain.models.shared import types
from backend.domain.models.shared.config import EngineConfig

# 从 shared.types 重新导出所有 WebSocket 和 API 类型
from backend.domain.models.shared.types import (
    APIAgentStatusData,
    APIAgentStatusItem,
    APIResumeData,
    APISendMessageData,
    APISkillItem,
    APIStopAgentData,
    WSDeltaContent,
    WSDialogMetadata,
    WSDialogSnapshot,
    WSErrorDetail,
    WSErrorEvent,
    WSMessageItem,
    WSRoundsLimitEvent,
    WSSnapshotEvent,
    WSStreamDeltaEvent,
    WSStreamingMessage,
    make_status_change,
)

__all__ = [
    "EngineConfig",
    "WSMessageItem",
    "WSDialogMetadata",
    "WSStreamingMessage",
    "WSDialogSnapshot",
    "WSSnapshotEvent",
    "WSStreamDeltaEvent",
    "WSDeltaContent",
    "WSErrorEvent",
    "WSErrorDetail",
    "WSRoundsLimitEvent",
    "make_status_change",
    "APISendMessageData",
    "APIResumeData",
    "APIAgentStatusItem",
    "APIAgentStatusData",
    "APIStopAgentData",
    "APISkillItem",
    "ToolCall",
    "Skill",
    "SkillDefinition",
]
