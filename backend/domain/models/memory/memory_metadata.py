"""
Memory Metadata - 记忆元数据模型

定义记忆的元数据结构，支持前端展示和缓存管理。
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """记忆类型枚举"""

    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"


class MemoryMetadata(BaseModel):
    """
    记忆元数据

    用于前端展示和缓存管理的轻量级元数据模型。

    Attributes:
        id: 记忆唯一ID
        user_id: 用户ID
        project_path: 项目路径
        type: 记忆类型
        name: 记忆名称
        description: 简短描述
        created_at: 创建时间
        updated_at: 更新时间
        age_days: 年龄（天数）
    """

    id: str = Field(..., description="记忆唯一ID")
    user_id: str = Field(..., description="用户ID")
    project_path: str = Field(default="", description="项目路径")
    type: MemoryType = Field(..., description="记忆类型")
    name: str = Field(..., description="记忆名称")
    description: str = Field(default="", description="简短描述")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    age_days: int = Field(default=0, description="年龄（天数）")
    confidence: float = Field(default=1.0, description="提取置信度")

    @property
    def is_fresh(self) -> bool:
        """检查是否新鲜（7天内）"""
        return self.age_days <= 7

    @property
    def freshness_text(self) -> str:
        """获取新鲜度文本"""
        if self.age_days == 0:
            return "today"
        elif self.age_days == 1:
            return "yesterday"
        else:
            return f"{self.age_days} days ago"

    @property
    def freshness_warning(self) -> str:
        """获取新鲜度警告（如果过期）"""
        if self.is_fresh:
            return ""
        return (
            f"⚠️ This memory is {self.freshness_text} old. "
            "Claims may be outdated."
        )

    class Config:
        extra = "allow"
