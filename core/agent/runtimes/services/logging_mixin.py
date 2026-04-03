"""
Deep Logging Mixin - Deep Agent 日志记录 Mixin

提供三种级别的日志记录：
- messages: AIMessage 级别日志
- updates: 节点更新日志
- values: 完整状态日志
"""
from typing import Any
from core.models.event_models import (
    AIMessageLogModel,
    ToolMessageLogModel,
    ToolStartDataModel,
)


class DeepLoggingMixin:
    """Deep Agent 日志记录 Mixin"""

    def _init_loggers(self) -> None:
        """初始化日志记录器"""
        from runtime.logging_config import (
            get_deep_msg_logger,
            get_deep_update_logger,
            get_deep_value_logger,
        )
        self._msg_logger = get_deep_msg_logger()
        self._update_logger = get_deep_update_logger()
        self._value_logger = get_deep_value_logger()

    def _log_values(self, event: Any, dialog_id: str) -> None:
        """记录 values 级别日志（完整状态）"""
        if not isinstance(event, dict):
            return

        messages = event.get("messages", [])
        todos = event.get("todos", [])
        interrupt = event.get("interrupt")

        self._value_logger.debug(
            "State update: dialog_id={}, message_count={}, todo_count={}, has_interrupt={}",
            dialog_id, len(messages), len(todos), interrupt is not None
        )

        if messages:
            last_msg = messages[-1]
            self._value_logger.debug(
                "Last message: type={}, id={}",
                getattr(last_msg, "type", "unknown"),
                getattr(last_msg, "id", "unknown")
            )

    def _log_messages_from_values(self, event: Any, dialog_id: str) -> None:
        """从 values 事件中提取并记录 messages 级别日志"""
        if not isinstance(event, dict):
            return

        messages = event.get("messages", [])
        if not messages:
            return

        last_msg = messages[-1]

        if hasattr(last_msg, "type") and last_msg.type == "ai":
            msg_data = AIMessageLogModel(
                role="assistant",
                content=getattr(last_msg, "content", "")[:200],
                tool_calls=getattr(last_msg, "tool_calls", []),
                metadata={
                    "dialog_id": dialog_id,
                    "message_id": getattr(last_msg, "id", None),
                    "usage_metadata": getattr(last_msg, "usage_metadata", None),
                    "response_metadata": getattr(last_msg, "response_metadata", None),
                }
            )
            self._msg_logger.debug("AIMessage: {}", msg_data.model_dump())

        elif hasattr(last_msg, "type") and last_msg.type == "tool":
            msg_data = ToolMessageLogModel(
                role="tool",
                content=getattr(last_msg, "content", "")[:200],
                tool_call_id=getattr(last_msg, "tool_call_id", ""),
                metadata={
                    "dialog_id": dialog_id,
                    "status": getattr(last_msg, "status", "unknown"),
                }
            )
            self._msg_logger.debug("ToolMessage: {}", msg_data.model_dump())

        elif hasattr(last_msg, "type") and last_msg.type == "human":
            self._msg_logger.debug(
                "HumanMessage: dialog_id={}, content_length={}",
                dialog_id, len(getattr(last_msg, "content", ""))
            )

    def _log_updates_from_values(self, event: Any, dialog_id: str) -> None:
        """从 values 事件中提取并记录 updates 级别日志"""
        if not isinstance(event, dict):
            return

        messages = event.get("messages", [])
        if not messages:
            return

        last_msg = messages[-1]
        msg_type = getattr(last_msg, "type", "unknown")

        if msg_type == "ai":
            self._update_logger.debug(
                "Node[generate]: dialog_id={}, content_length={}",
                dialog_id, len(getattr(last_msg, "content", ""))
            )
        elif msg_type == "tool":
            self._update_logger.debug(
                "Node[tools]: dialog_id={}, tool_call_id={}",
                dialog_id, getattr(last_msg, "tool_call_id", "unknown")
            )

    def _log_message_chunk(self, event: Any, dialog_id: str, accumulated: str) -> None:
        """记录消息块日志"""
        chunk_size = len(getattr(event, "content", "")) if hasattr(event, "content") else 0
        self._msg_logger.debug(
            "Token stream: dialog_id={}, chunk_size={}, accumulated={},content{}",
            dialog_id, chunk_size, len(accumulated),accumulated
        )

    def _log_tool_start(self, event: Any, dialog_id: str) -> None:
        """记录工具开始日志"""
        tool_name = getattr(event, "name", "unknown")
        tool_data = ToolStartDataModel(
            name=tool_name,
            args=getattr(event, "arguments", {}),
            tool_call_id=getattr(event, "tool_call_id", None),
        )
        self._msg_logger.debug("Tool start: dialog_id={}, {}", dialog_id, tool_data.model_dump())
        self._update_logger.debug(
            "Node[tools]: dialog_id={}, tool={}",
            dialog_id, tool_name
        )

    def _log_tool_end(self, event: Any, dialog_id: str) -> None:
        """记录工具结束日志"""
        self._msg_logger.debug(
            "Tool end: dialog_id={}, tool_call_id={}, result_length={}",
            dialog_id,
            getattr(event, "tool_call_id", "unknown"),
            len(str(getattr(event, "result", "")))
        )
