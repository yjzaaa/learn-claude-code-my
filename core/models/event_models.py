"""
Event Models - Pydantic 事件模型

用于 deep_runtime 和其他组件的 Pydantic 事件模型定义。
"""

from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field


class UserMessageModel(BaseModel):
    """用户消息模型"""
    role: str = "user"
    content: str
    metadata: Optional[Dict[str, Any]] = None


class AIMessageLogModel(BaseModel):
    """AI 消息日志模型"""
    role: str = "assistant"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolMessageLogModel(BaseModel):
    """工具消息日志模型"""
    role: str = "tool"
    content: str
    tool_call_id: str
    metadata: Optional[Dict[str, Any]] = None


class ToolStartDataModel(BaseModel):
    """工具开始数据模型"""
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    tool_call_id: Optional[str] = None


class LangGraphConfigModel(BaseModel):
    """LangGraph 配置模型"""
    thread_id: Optional[str] = None
    checkpoint_ns: Optional[str] = None
    checkpoint_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


__all__ = [
    "UserMessageModel",
    "AIMessageLogModel",
    "ToolMessageLogModel",
    "ToolStartDataModel",
    "LangGraphConfigModel",
]
