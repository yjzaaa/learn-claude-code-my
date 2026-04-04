"""
Message DTOs - 消息数据传输对象

OpenAI 格式的消息相关 DTOs。
"""
from typing import Optional, List
from pydantic import BaseModel


class ToolCallFunctionDTO(BaseModel):
    """OpenAI 格式的工具调用函数定义"""
    name: str
    arguments: str


class ToolCallDTO(BaseModel):
    """OpenAI 格式的工具调用 DTO"""
    id: str
    type: str = "function"
    function: ToolCallFunctionDTO


class MessageDTO(BaseModel):
    """消息 DTO (OpenAI 格式)"""
    role: str
    content: str
    tool_calls: Optional[List[ToolCallDTO]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
