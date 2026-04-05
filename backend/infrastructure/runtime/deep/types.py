"""Deep Runtime Types - 共享类型定义

定义 Deep Agent Runtime 使用的共享类型和数据类。
"""

from typing import Any, Optional, Callable
from dataclasses import dataclass

from pydantic import BaseModel


class DeepAgentConfig(BaseModel):
    """Deep Agent 配置"""
    name: str = "deep_agent"
    model: str = "claude-sonnet-4-6"
    system: str = ""
    system_prompt: str = ""
    skills: list[str] = []
    subagents: list[str] = []
    interrupt_on: dict[str, Any] = {}


@dataclass
class ToolCache:
    """工具缓存"""
    handler: Callable[..., Any]
    description: str
    parameters_schema: dict[str, Any]


@dataclass
class StreamingState:
    """流式状态"""
    accumulated_content: str = ""
    accumulated_reasoning: str = ""
    last_message_id: Optional[str] = None
    actual_model_name: Optional[str] = None


__all__ = ["DeepAgentConfig", "ToolCache", "StreamingState"]
