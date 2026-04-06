"""
Skill Engine Types - Skill Engine 类型定义

包含 Skill Engine 所需的所有数据类型和常量定义。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ==================== 常量定义 ====================

PREFILTER_THRESHOLD: int = 10
"""BM25 预过滤阈值：候选技能数超过此值时才使用 embedding 重排序"""

SKILL_EMBEDDING_MODEL: str = "openai/text-embedding-3-small"
"""默认技能 embedding 模型"""

SKILL_EMBEDDING_MAX_CHARS: int = 12_000
"""技能文本最大字符数（截断长度）"""

BM25_CANDIDATES_MULTIPLIER: int = 3
"""BM25 候选数倍数：top_k * 3"""

DEFAULT_MAX_SKILL_SELECT: int = 2
"""默认最大选择技能数"""

SKILL_QUALITY_FILTER_NEVER_COMPLETED_THRESHOLD: int = 2
"""从未完成过滤阈值：selections >= 2 且 completions == 0"""

SKILL_QUALITY_FILTER_FALLBACK_RATIO_THRESHOLD: float = 0.5
"""高回退率过滤阈值：fallbacks / applied > 0.5"""

SKILL_QUALITY_FILTER_MIN_APPLIED: int = 2
"""高回退率过滤最小应用次数"""


# ==================== 枚举类型 ====================


class SkillOrigin(Enum):
    """技能来源类型"""

    IMPORTED = "imported"  # 导入的技能
    EVOLVED = "evolved"  # 进化生成的技能
    DERIVED = "derived"  # 从成功模式提取的技能
    CAPTURED = "captured"  # 捕获的用户行为


class SkillExecutionStatus(Enum):
    """技能执行状态"""

    SELECTED = "selected"  # 被 LLM 选中
    APPLIED = "applied"  # 实际应用到对话
    COMPLETED = "completed"  # 成功完成任务
    FALLBACK = "fallback"  # 触发回退


# ==================== 数据类定义 ====================


@dataclass
class SkillCandidate:
    """技能候选，用于排序和选择"""

    skill_id: str
    name: str
    description: str
    body: str = ""
    bm25_score: float = 0.0
    embedding_score: float = 0.0
    hybrid_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_embedding_text(self) -> str:
        """生成用于 embedding 的文本"""
        body_truncated = self.body[:8000] if self.body else ""
        return f"{self.name}\n{self.description}\n\n{body_truncated}"


@dataclass
class SkillMeta:
    """技能元数据（存储在 sidecar 中）"""

    skill_id: str
    name: str
    origin: SkillOrigin = SkillOrigin.IMPORTED
    generation: int = 1  # 进化代数（v1, v2, ...）
    parent_id: str | None = None  # 父技能 ID（用于进化追踪）
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "origin": self.origin.value,
            "generation": self.generation,
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillMeta":
        """从字典创建"""
        return cls(
            skill_id=data["skill_id"],
            name=data["name"],
            origin=SkillOrigin(data.get("origin", "imported")),
            generation=data.get("generation", 1),
            parent_id=data.get("parent_id"),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if "updated_at" in data
            else datetime.utcnow(),
        )


@dataclass
class ExecutionAnalysis:
    """执行分析结果"""

    success: bool
    error_pattern: str | None = None
    suggested_improvement: str | None = None
    candidate_for_evolution: bool = False
    execution_time_ms: int = 0
    tool_calls_count: int = 0


@dataclass
class SkillQualityRecord:
    """技能质量记录（单条）"""

    skill_id: str
    task_id: str
    status: SkillExecutionStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSONL 存储）"""
        return {
            "skill_id": self.skill_id,
            "task_id": self.task_id,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillQualityRecord":
        """从字典创建"""
        return cls(
            skill_id=data["skill_id"],
            task_id=data["task_id"],
            status=SkillExecutionStatus(data["status"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SkillQualityMetrics:
    """技能质量指标（聚合）"""

    skill_id: str
    total_selections: int = 0
    total_applied: int = 0
    total_completions: int = 0
    total_fallbacks: int = 0

    @property
    def completion_rate(self) -> float:
        """完成率（应用后成功完成的比例）"""
        if self.total_applied == 0:
            return 0.0
        return self.total_completions / self.total_applied

    @property
    def fallback_rate(self) -> float:
        """回退率（应用后触发回退的比例）"""
        if self.total_applied == 0:
            return 0.0
        return self.total_fallbacks / self.total_applied

    @property
    def is_problematic(self) -> bool:
        """是否是有问题的技能（需要过滤）"""
        # 规则1: 多次选中但从未完成
        if (
            self.total_selections >= SKILL_QUALITY_FILTER_NEVER_COMPLETED_THRESHOLD
            and self.total_completions == 0
        ):
            return True

        # 规则2: 应用后高回退率
        if (
            self.total_applied >= SKILL_QUALITY_FILTER_MIN_APPLIED
            and self.fallback_rate > SKILL_QUALITY_FILTER_FALLBACK_RATIO_THRESHOLD
        ):
            return True

        return False

    def to_summary_dict(self) -> dict[str, Any]:
        """生成摘要字典"""
        return {
            "skill_id": self.skill_id,
            "total_selections": self.total_selections,
            "total_applied": self.total_applied,
            "total_completions": self.total_completions,
            "total_fallbacks": self.total_fallbacks,
            "completion_rate": round(self.completion_rate, 2),
            "fallback_rate": round(self.fallback_rate, 2),
            "is_problematic": self.is_problematic,
        }
