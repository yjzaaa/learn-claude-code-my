"""
Artifact - 产物实体

代码、文档等产物的领域模型。
"""
from typing import Optional
from core.models.base import Entity, generate_id
from core.models.mixins import DialogRefMixin


class Artifact(Entity, DialogRefMixin):
    """产物 (代码、文档等)"""
    type: str  # "code", "document", "data", etc.
    name: str
    content: str
    language: Optional[str] = None

    @classmethod
    def create(
        cls,
        type: str,
        name: str,
        content: str,
        language: Optional[str] = None,
        dialog_id: Optional[str] = None,
    ) -> "Artifact":
        """创建产物实例"""
        return cls(
            id=generate_id("art"),
            type=type,
            name=name,
            content=content,
            language=language,
            dialog_id=dialog_id or "",
        )
