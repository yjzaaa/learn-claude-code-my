"""
Memory Entity - 记忆实体

记忆系统的核心实体，存储从对话中提取的有价值信息。
支持多用户隔离和项目作用域。
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from backend.domain.models.memory.types import MemoryType
from backend.domain.models.shared.base import Entity


class Memory(Entity):
    """
    记忆实体

    表示一条从对话中提取的记忆，包含类型、内容、元数据等信息。
    支持多用户隔离（通过 user_id）和项目作用域（通过 project_path）。

    Attributes:
        user_id: 用户ID，用于多用户数据隔离
        project_path: 项目路径，用于项目作用域
        type: 记忆类型（user/feedback/project/reference）
        name: 记忆名称/标题
        description: 简短描述（单行）
        content: 记忆详细内容
        created_at: 创建时间
        updated_at: 更新时间
    """

    user_id: str = Field(..., description="用户ID，用于数据隔离")
    project_path: str = Field(default="", description="项目路径，用于作用域")
    type: MemoryType = Field(..., description="记忆类型")
    name: str = Field(..., description="记忆名称/标题")
    description: str = Field(default="", description="简短描述")
    content: str = Field(..., description="记忆详细内容")
    source_dialog_id: Optional[str] = Field(default=None, description="来源对话ID")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="提取置信度")

    def update_content(self, new_content: str) -> None:
        """更新记忆内容并刷新时间戳"""
        self.content = new_content
        self.touch()

    @property
    def age_days(self) -> int:
        """计算记忆年龄（天数）"""
        from datetime import datetime

        delta = datetime.now() - self.updated_at
        return max(0, delta.days)

    @property
    def is_fresh(self) -> bool:
        """检查记忆是否新鲜（7天内更新）"""
        return self.age_days <= 7

    def to_prompt_text(self) -> str:
        """转换为提示词文本格式"""
        freshness = "[fresh]" if self.is_fresh else f"[{self.age_days} days old]"
        return f"[{self.type.value}] {self.name} {freshness}\n{self.content}"

    class Config(Entity.Config):
        pass
