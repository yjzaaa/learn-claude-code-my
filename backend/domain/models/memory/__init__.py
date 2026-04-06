"""
Memory Models - 记忆系统模型

定义记忆系统的核心数据模型，包括四种记忆类型：
- user: 用户信息（角色、偏好等）
- feedback: 反馈指导（行为规则、改进建议等）
- project: 项目上下文（目标、约束、截止日期等）
- reference: 外部引用（文档链接、资源位置等）
"""

from backend.domain.models.memory.memory import Memory
from backend.domain.models.memory.memory_metadata import MemoryMetadata
from backend.domain.models.memory.privacy_config import (
    MemoryPrivacyConfig,
    PrivacyMode,
    SyncStrategy,
    TypePrivacySettings,
    UserPrivacyPreferences,
)
from backend.domain.models.memory.types import MemoryType

__all__ = [
    "MemoryType",
    "Memory",
    "MemoryMetadata",
    "PrivacyMode",
    "SyncStrategy",
    "TypePrivacySettings",
    "MemoryPrivacyConfig",
    "UserPrivacyPreferences",
]
