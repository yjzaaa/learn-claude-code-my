"""Event Stream Handler - 事件流处理

处理流式响应的事件解析和转发。
"""

from collections.abc import AsyncIterator
from typing import Any

from backend.domain.models.shared import AgentEvent
from backend.infrastructure.logging import get_logger

from .types import StreamingState

logger = get_logger(__name__)


class EventStreamHandler:
    """事件流处理器

    职责:
    - 解析流式响应
    - 提取内容和推理
    - 构建 AgentEvent
    """

    def __init__(self, dialog_id: str, message_id: str):
        self.dialog_id = dialog_id
        self.message_id = message_id
        self.state = StreamingState()

    async def process_stream(
        self,
        stream_iterator: AsyncIterator[Any],
    ) -> AsyncIterator[AgentEvent]:
        """处理流式响应

        Args:
            stream_iterator: 原始流迭代器

        Yields:
            AgentEvent 事件
        """
        async for raw_event in stream_iterator:
            events = self._process_raw_event(raw_event)
            for event in events:
                yield event

    def _process_raw_event(self, raw_event: Any) -> list:
        """处理单个原始事件"""
        events = []

        # 解析不同格式的 raw_event
        msg_chunk = self._extract_message_chunk(raw_event)
        if not msg_chunk:
            return events

        # 处理 ToolMessage
        if getattr(msg_chunk, "type", None) == "tool":
            events.append(self._build_tool_result_event(msg_chunk))
            return events

        # 处理工具调用
        if getattr(msg_chunk, "type", None) in ("ai", "assistant"):
            tool_calls = getattr(msg_chunk, "tool_calls", None) or []
            for tc in tool_calls:
                events.append(self._build_tool_call_event(tc))

        # 提取内容
        delta_content = self._extract_content(msg_chunk)
        if delta_content:
            self.state.accumulated_content += delta_content
            events.append(
                AgentEvent(
                    type="text_delta",
                    data=delta_content,
                    metadata={"accumulated_length": len(self.state.accumulated_content)},
                )
            )

        # 提取推理
        delta_reasoning = self._extract_reasoning(msg_chunk)
        if delta_reasoning:
            self.state.accumulated_reasoning += delta_reasoning
            events.append(
                AgentEvent(
                    type="reasoning_delta",
                    data=delta_reasoning,
                    metadata={"accumulated_length": len(self.state.accumulated_reasoning)},
                )
            )

        return events

    def _extract_message_chunk(self, raw_event: Any) -> Any | None:
        """提取消息块"""
        if isinstance(raw_event, tuple) and len(raw_event) >= 2:
            msg_chunk = raw_event[1]
            if isinstance(msg_chunk, tuple):
                return msg_chunk[0]
            return msg_chunk
        return raw_event

    def _extract_content(self, msg_chunk: Any) -> str:
        """提取内容"""
        content = getattr(msg_chunk, "content", "")
        if not content:
            return ""

        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            return "".join(parts)
        return str(content)

    def _extract_reasoning(self, msg_chunk: Any) -> str:
        """提取推理内容"""
        additional_kwargs = getattr(msg_chunk, "additional_kwargs", {})
        reasoning = additional_kwargs.get("reasoning_content", "")
        return str(reasoning) if reasoning else ""

    def _build_tool_result_event(self, msg_chunk: Any) -> AgentEvent:
        """构建工具结果事件"""
        return AgentEvent(
            type="tool_result",
            data={
                "tool_name": getattr(msg_chunk, "name", "unknown"),
                "tool_call_id": getattr(msg_chunk, "tool_call_id", "unknown"),
                "result": str(getattr(msg_chunk, "content", "")),
            },
            metadata={"tool_call_id": getattr(msg_chunk, "tool_call_id", "unknown")},
        )

    def _build_tool_call_event(self, tc: dict) -> AgentEvent:
        """构建工具调用事件"""
        tc_args = tc.get("args", {})
        if isinstance(tc_args, str):
            try:
                import json

                tc_args = json.loads(tc_args)
            except Exception:
                tc_args = {"raw": tc_args}

        return AgentEvent(
            type="tool_call",
            data={
                "message_id": self.message_id,
                "tool_call": {
                    "id": tc.get("id", "call_0"),
                    "name": tc.get("name", "unknown"),
                    "arguments": tc_args,
                    "status": "pending",
                },
            },
        )

    def build_completion_event(self, model_name: str, provider: str) -> AgentEvent:
        """构建完成事件"""
        return AgentEvent(
            type="message_complete",
            data=self.state.accumulated_content,
            metadata={
                "reasoning_content": self.state.accumulated_reasoning,
                "model": model_name or "unknown",
                "provider": provider,
                "content_length": len(self.state.accumulated_content),
            },
        )


__all__ = ["EventStreamHandler"]
