"""Pydantic schemas for metadata and responses.

强制使用模型替代裸字典，确保数据结构可验证、可维护。
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class CompletionMetadata(BaseModel):
    """AI 响应完成的元数据结构"""
    model: str = Field(description="使用的模型名称")
    provider: str = Field(default="unknown", description="模型提供商")
    reasoning_content: Optional[str] = Field(default=None, description="推理内容")
    content_length: int = Field(default=0, description="内容长度")

    class Config:
        frozen = True  # 不可变，防止运行时修改


class CheckpointSnapshot(BaseModel):
    """Checkpoint 快照数据结构"""
    dialog_id: str
    model: str = Field(default="unknown", description="实际使用的模型名称")
    checkpoint_exists: bool = True
    messages_count: int = 0
    timestamp: Optional[str] = None

    class Config:
        extra = "allow"  # 允许额外字段（checkpoint 数据可能变化）


class ToolCallMetadata(BaseModel):
    """工具调用元数据"""
    tool_name: str
    tool_call_id: str
    arguments: dict[str, Any]
    status: str = "pending"  # pending, success, error


class StreamEventMetadata(BaseModel):
    """流式事件元数据"""
    event_type: str
    dialog_id: Optional[str] = None
    timestamp: Optional[str] = None
    raw_event: Optional[dict] = None
