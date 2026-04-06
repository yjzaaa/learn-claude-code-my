"""
Data Containers - 数据容器

通用数据容器模型。
"""

from typing import Any

from pydantic import BaseModel, Field


class ResultData(BaseModel):
    """通用结果数据容器"""

    items: list[dict[str, Any]] = Field(default_factory=list)


class ProposalData(BaseModel):
    """提案数据容器"""

    proposals: list[dict[str, Any]] = Field(default_factory=list)


class TodoListData(BaseModel):
    """Todo 列表数据容器"""

    items: list[dict[str, Any]] = Field(default_factory=list)
    enabled: bool = True


class Metadata(BaseModel):
    """通用元数据容器"""

    data: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class ItemData(BaseModel):
    """通用数据项容器"""

    data: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class ToolItem(BaseModel):
    """工具项容器"""

    data: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"
