"""
Domain Models - 核心领域模型

合并 Artifact 和 Skill 两类小型领域对象。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

try:
    from dataclasses_json import dataclass_json  # type: ignore[import-not-found]
except ImportError:
    def dataclass_json(cls):  # type: ignore[no-redef]
        return cls


# ═══════════════════════════════════════════════════════════
# Artifact
# ═══════════════════════════════════════════════════════════

@dataclass_json
@dataclass
class Artifact:
    """产物 (代码、文档等)"""
    id: str
    type: str  # "code", "document", "data", etc.
    name: str
    content: str
    language: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    dialog_id: Optional[str] = None

    @classmethod
    def create(
        cls,
        type: str,
        name: str,
        content: str,
        language: Optional[str] = None,
        dialog_id: Optional[str] = None,
    ) -> "Artifact":
        return cls(
            id=f"art_{uuid.uuid4().hex[:12]}",
            type=type,
            name=name,
            content=content,
            language=language,
            dialog_id=dialog_id,
        )


# ═══════════════════════════════════════════════════════════
# Skill
# ═══════════════════════════════════════════════════════════

@dataclass_json
@dataclass
class SkillDefinition:
    """技能定义"""
    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass_json
@dataclass
class Skill:
    """技能实例"""
    id: str
    definition: SkillDefinition
    path: Optional[str] = None
    loaded_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    scripts_loaded: bool = False  # 懒加载标记

    @property
    def name(self) -> str:
        return self.definition.name
