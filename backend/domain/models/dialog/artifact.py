"""
Artifact - 产物实体

代码、文档等产物的领域模型。
"""

from backend.domain.models.shared.base import Entity, generate_id
from backend.domain.models.shared.mixins import DialogRefMixin


class Artifact(Entity, DialogRefMixin):
    """产物 (代码、文档等)"""

    type: str  # "code", "document", "data", etc.
    name: str
    content: str
    language: str | None = None

    @classmethod
    def create(
        cls,
        type: str,
        name: str,
        content: str,
        language: str | None = None,
        dialog_id: str | None = None,
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
