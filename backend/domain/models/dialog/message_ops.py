"""Message Operations - 消息操作

处理消息的添加、获取和格式转换。
"""

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from backend.infrastructure.logging import get_logger

from .session import DialogSession

logger = get_logger(__name__)


class MessageOperations:
    """消息操作类

    职责:
    - 添加用户/助手/工具消息
    - 获取消息列表
    - 消息格式转换
    """

    async def add_user_message(
        self,
        session: DialogSession,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> HumanMessage:
        """添加用户消息"""
        msg = HumanMessage(
            content=content,
            additional_kwargs=metadata or {},
        )
        session.history.add_message(msg)
        session.metadata.message_count += 1
        session.metadata.token_count += len(content) // 4 + 10
        session.touch()

        logger.debug(f"[MessageOps] Added user message to {session.dialog_id}")
        return msg

    async def add_assistant_message(
        self,
        session: DialogSession,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> AIMessage:
        """添加助手消息"""
        msg = AIMessage(
            content=content,
            additional_kwargs=metadata or {},
        )
        session.history.add_message(msg)
        session.metadata.message_count += 1
        session.metadata.token_count += len(content) // 4 + 10
        session.touch()

        logger.debug(f"[MessageOps] Added assistant message to {session.dialog_id}")
        return msg

    async def add_tool_result(
        self,
        session: DialogSession,
        tool_call_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ToolMessage:
        """添加工具执行结果"""
        msg = ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            additional_kwargs=metadata or {},
        )
        session.history.add_message(msg)
        session.metadata.tool_calls_count += 1
        session.touch()

        logger.debug(f"[MessageOps] Added tool result to {session.dialog_id}")
        return msg

    def get_messages(
        self,
        session: DialogSession,
        limit: int | None = None,
    ) -> list[BaseMessage]:
        """获取消息列表"""
        messages = list(session.history.messages)
        if limit:
            messages = messages[-limit:]
        return messages

    def get_messages_for_llm(
        self,
        session: DialogSession,
        max_tokens: int = 8000,
    ) -> list[BaseMessage]:
        """获取 LLM 可用的消息格式（带 token 截断）。

        返回 LangChain 消息对象列表（LangGraph 需要原始消息对象）。
        """
        messages = list(session.history.messages)

        total_tokens = 0
        result = []
        for msg in reversed(messages):
            msg_tokens = len(msg.content) // 4 + 10 if msg.content else 10
            if total_tokens + msg_tokens > max_tokens:
                break
            total_tokens += msg_tokens
            result.insert(0, msg)

        return result


__all__ = ["MessageOperations"]
