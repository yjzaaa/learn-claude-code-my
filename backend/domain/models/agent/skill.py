"""
Skill - 技能实体

技能定义和实例的领域模型。
"""

from typing import Any

from pydantic import BaseModel, Field

from backend.domain.models.shared.base import Entity


class SkillDefinition(BaseModel):
    """技能定义"""

    name: str
    description: str
    version: str = "1.0.0"
    author: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class Skill(Entity):
    """技能实例"""

    definition: SkillDefinition
    path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    scripts_loaded: bool = False  # 懒加载标记

    @property
    def name(self) -> str:
        return self.definition.name
