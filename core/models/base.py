"""
Base Models - 模型基类定义

定义所有模型的公共基类，使用继承减少重复代码。
"""

import time
import uuid
from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EventPriority(IntEnum):
    """事件优先级"""
    CRITICAL = 0    # 关键事件，立即处理
    HIGH = 1        # 高优先级
    NORMAL = 2      # 正常优先级
    LOW = 3         # 低优先级
    BACKGROUND = 4  # 后台任务


def generate_id(prefix: str = "") -> str:
    """生成唯一 ID"""
    id_str = uuid.uuid4().hex[:12]
    return f"{prefix}_{id_str}" if prefix else id_str


class Entity(BaseModel):
    """
    业务实体基类

    所有业务实体（Dialog, Message, Artifact, Skill 等）的基类。
    提供统一的 ID 和时间戳管理。
    """
    id: str = Field(default_factory=lambda: generate_id())
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def touch(self) -> None:
        """更新时间戳"""
        self.updated_at = datetime.now()

    class Config:
        extra = "allow"


class Event(BaseModel):
    """
    事件基类

    所有事件类型的基类。提供统一的事件字段和序列化。
    """
    type: str = Field(default="", description="事件类型标识")
    dialog_id: str = Field(default="", description="关联对话 ID")
    timestamp: float = Field(default_factory=time.time, description="事件时间戳")
    priority: EventPriority = Field(default=EventPriority.NORMAL, description="事件优先级")

    @property
    def event_type(self) -> str:
        """事件类型名称（类名）"""
        return self.type or self.__class__.__name__

    class Config:
        extra = "allow"


class Response(BaseModel):
    """
    API 响应基类

    所有 API 响应模型的基类，提供统一的成功/失败标识。
    """
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(default="", description="响应消息")

    @classmethod
    def ok(cls, message: str = "ok", **kwargs) -> "Response":
        """创建成功响应"""
        return cls(success=True, message=message, **kwargs)

    @classmethod
    def error(cls, message: str = "error", **kwargs) -> "Response":
        """创建错误响应"""
        return cls(success=False, message=message, **kwargs)


class Config(BaseModel):
    """
    配置基类

    所有配置类的基类，支持从字典创建。
    """

    @classmethod
    def from_dict(cls, config: Optional[Dict[str, Any]] = None) -> "Config":
        """从字典创建配置"""
        if not config:
            return cls()
        return cls.model_validate(config)

    class Config:
        extra = "allow"
        arbitrary_types_allowed = True


# ═══════════════════════════════════════════════════════════
# 向后兼容别名
# ═══════════════════════════════════════════════════════════

BaseEvent = Event

__all__ = [
    "EventPriority",
    "generate_id",
    "Entity",
    "Event",
    "BaseEvent",
    "Response",
    "Config",
]
