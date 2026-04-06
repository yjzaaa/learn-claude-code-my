"""
Stats Models - 统计模型

来自 stats_models.py 的统计相关模型。
"""

from pydantic import BaseModel, Field


class MemoryStats(BaseModel):
    """记忆统计信息模型"""

    short_term_dialogs: int = 0
    short_term_entries: int = 0
    long_term_entries: int = 0
    summaries: int = 0


class SkillStats(BaseModel):
    """技能统计信息模型"""

    loaded_skills: int = 0
    skill_ids: list[str] = Field(default_factory=list)
    total_tools: int = 0


class EventBusStats(BaseModel):
    """事件总线统计信息模型"""

    running: bool = False
    typed_subscribers: dict[str, int] = Field(default_factory=dict)
    global_subscribers: int = 0
    total_subscribers: int = 0
