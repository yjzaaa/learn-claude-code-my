"""
Message Models - 消息相关模型

包含消息评分系统等功能。
"""

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MessageRating(BaseModel):
    """
    消息评分模型

    用户可以给 AI 消息打分（1-5 星），并添加可选的评论。
    """

    id: str = Field(default_factory=lambda: f"rating_{uuid.uuid4().hex[:12]}")
    message_id: str = Field(..., description="被评分的消息 ID")
    score: int = Field(..., ge=1, le=5, description="评分分数（1-5 星）")
    comment: str | None = Field(default=None, max_length=1000, description="可选的评论")
    created_at: float = Field(default_factory=time.time, description="评分时间戳")

    @field_validator("message_id")
    @classmethod
    def validate_message_id(cls, v: str) -> str:
        """验证 message_id 不为空"""
        if not v or not v.strip():
            raise ValueError("message_id cannot be empty")
        return v

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        """验证评分在 1-5 范围内"""
        if v < 1 or v > 5:
            raise ValueError("score must be between 1 and 5")
        return v

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageRating":
        """从字典创建实例"""
        return cls.model_validate(data)


def calculate_average_rating(ratings: list[dict[str, Any]]) -> float | None:
    """
    计算平均评分

    Args:
        ratings: 评分列表，每个评分是一个包含 "score" 键的字典

    Returns:
        平均评分（保留一位小数），如果列表为空则返回 None
    """
    if not ratings:
        return None

    scores = [r["score"] for r in ratings if "score" in r]
    if not scores:
        return None

    avg = sum(scores) / len(scores)
    return round(avg, 1)


def get_rating_distribution(ratings: list[dict[str, Any]]) -> dict[int, int]:
    """
    获取评分分布

    Args:
        ratings: 评分列表

    Returns:
        每个星级（1-5）的出现次数字典
    """
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for rating in ratings:
        score = rating.get("score")
        if isinstance(score, int) and 1 <= score <= 5:
            distribution[score] += 1

    return distribution


__all__ = [
    "MessageRating",
    "calculate_average_rating",
    "get_rating_distribution",
]
