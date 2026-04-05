"""
Mixins - 可复用模型组件

通过 Mixin 模式提供可组合的公共字段，避免重复定义。
"""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field

from .base_mixins import (
    ComparableMixin,
    SerializableMixin,
    ValidatableMixin,
    LoggerMixin,
)


class TimestampMixin(BaseModel):
    """
    时间戳 Mixin

    添加创建时间和更新时间字段。
    """
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def touch(self) -> None:
        """更新时间戳"""
        self.updated_at = datetime.now()


class DialogRefMixin(BaseModel):
    """
    对话引用 Mixin

    添加对话 ID 引用字段。
    """
    dialog_id: str = Field(default="", description="关联对话 ID")


class MetadataMixin(BaseModel):
    """
    元数据 Mixin

    添加通用元数据容器字段。
    """
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="通用元数据容器"
    )


class IdMixin(BaseModel):
    """
    ID Mixin

    添加 ID 字段。
    """
    id: str = Field(default="", description="唯一标识符")


__all__ = [
    # 基础 Mixin
    "ComparableMixin",
    "SerializableMixin",
    "ValidatableMixin",
    "LoggerMixin",
    # 领域 Mixin
    "TimestampMixin",
    "DialogRefMixin",
    "MetadataMixin",
    "IdMixin",
]
