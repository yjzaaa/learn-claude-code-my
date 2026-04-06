"""
ToolCall - 工具调用实体

工具调用状态和输出的领域模型。
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ToolCallOutput(BaseModel):
    """工具调用输出模型"""

    id: str
    name: str
    arguments: dict[str, Any]
    result: str | None = None
    error: str | None = None
    duration_ms: int | None = None


class ToolCall:
    """
    工具调用对象

    跟踪单个工具调用的状态和执行结果。
    """

    def __init__(
        self,
        id: str,
        name: str,
        arguments: dict[str, Any],
    ):
        self.id = id
        self.name = name
        self.arguments = arguments
        self.result: str | None = None
        self.error: str | None = None
        self.duration_ms: int | None = None
        self._start_time: datetime | None = None

    @classmethod
    def create(cls, name: str, arguments: dict[str, Any]) -> "ToolCall":
        """创建工具调用实例"""
        return cls(
            id=f"call_{uuid.uuid4().hex[:16]}",
            name=name,
            arguments=arguments,
        )

    def start(self) -> None:
        """开始执行计时"""
        self._start_time = datetime.now()

    def complete(self, result: str) -> None:
        """标记为完成"""
        self.result = result
        if self._start_time:
            self.duration_ms = int((datetime.now() - self._start_time).total_seconds() * 1000)

    def fail(self, error: str) -> None:
        """标记为失败"""
        self.error = error
        if self._start_time:
            self.duration_ms = int((datetime.now() - self._start_time).total_seconds() * 1000)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        output = ToolCallOutput(
            id=self.id,
            name=self.name,
            arguments=self.arguments,
            result=self.result,
            error=self.error,
            duration_ms=self.duration_ms,
        )
        return output.model_dump()
