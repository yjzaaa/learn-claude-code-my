"""
Dialog Manager - 对话管理器

管理对话的生命周期：创建、消息发送、状态查询。
通过事件总线解耦其他模块。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from backend.domain.models.dialog.dialog import Dialog
from backend.domain.models.message.message import Message
from backend.domain.models.events.base import (
    DialogClosed,
    DialogCreated,
    MessageCompleted,
    MessageReceived,
    StreamDelta,
)
from backend.domain.models.shared.config import DialogConfig
from backend.domain.models.shared.types import MessageDict
from backend.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from backend.infrastructure.event_bus import EventBus
    from backend.infrastructure.services.state_manager import StateManager

logger = get_logger(__name__)


class DialogManager:
    """
    对话管理器

    职责:
    - 创建和管理对话实例
    - 处理消息流
    - 维护对话状态

    依赖:
    - EventBus: 发送事件通知
    - StateManager: 持久化状态 (可选)
    """

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: StateManager | None = None,
        config: DialogConfig | None = None,
    ):
        self._event_bus = event_bus
        self._state_mgr = state_manager
        self._config = config or DialogConfig()

        # 内存中的活动对话
        self._dialogs: dict[str, Dialog] = {}

        # 配置
        self._max_history = self._config.max_history
        self._token_threshold = self._config.token_threshold

    async def create(self, user_input: str, title: str | None = None) -> str:
        """
        创建新对话

        Args:
            user_input: 用户初始输入
            title: 对话标题 (可选)

        Returns:
            对话 ID
        """
        if user_input:
            dialog = Dialog.from_user_input(user_input)
        else:
            dialog = Dialog.create(title=title or "New Dialog")
        if title:
            dialog.title = title

        self._dialogs[dialog.id] = dialog

        # 发射事件
        self._event_bus.emit(DialogCreated(dialog_id=dialog.id, user_input=user_input))

        logger.info(f"[DialogManager] Created dialog {dialog.id}")
        return dialog.id

    def get(self, dialog_id: str) -> Dialog | None:
        """
        获取对话

        Args:
            dialog_id: 对话 ID

        Returns:
            对话实例或 None
        """
        return self._dialogs.get(dialog_id)

    def list_dialogs(self) -> list[Dialog]:
        """
        列出所有对话

        Returns:
            对话列表 (按更新时间排序)
        """
        return sorted(self._dialogs.values(), key=lambda d: d.updated_at, reverse=True)

    async def add_user_message(self, dialog_id: str, content: str) -> Message:
        """
        添加用户消息

        Args:
            dialog_id: 对话 ID
            content: 消息内容

        Returns:
            创建的消息
        """
        dialog = self._get_dialog(dialog_id)
        message = Message.user(content)
        dialog.add_message(message)

        # 发射事件
        self._event_bus.emit(
            MessageReceived(dialog_id=dialog_id, message_id=message.id, content=content)
        )

        return message

    async def add_assistant_message(
        self,
        dialog_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        message_id: str | None = None,
    ) -> Message:
        """
        添加助手消息

        Args:
            dialog_id: 对话 ID
            content: 消息内容
            metadata: 元数据
            message_id: 指定消息 ID (用于与流式占位符对齐)

        Returns:
            创建的消息
        """
        dialog = self._get_dialog(dialog_id)
        message = Message.assistant(content, message_id=message_id, **(metadata or {}))
        dialog.add_message(message)

        # 发射完成事件
        self._event_bus.emit(
            MessageCompleted(
                dialog_id=dialog_id,
                message_id=message.id,
                content=content,
                token_count=dialog.estimate_tokens(),
            )
        )

        return message

    async def stream_assistant_response(
        self, dialog_id: str, stream_iterator: AsyncIterator[str]
    ) -> str:
        """
        流式添加助手响应

        Args:
            dialog_id: 对话 ID
            stream_iterator: 流式内容迭代器

        Returns:
            完整响应内容
        """
        dialog = self._get_dialog(dialog_id)
        full_content = []

        async for delta in stream_iterator:
            full_content.append(delta)

            # 发射流事件
            self._event_bus.emit(StreamDelta(dialog_id=dialog_id, delta=delta))

        # 添加完整消息
        content = "".join(full_content)
        message = Message.assistant(content)
        dialog.add_message(message)

        # 发射完成事件
        self._event_bus.emit(
            MessageCompleted(
                dialog_id=dialog_id,
                message_id=message.id,
                content=content,
                token_count=dialog.estimate_tokens(),
            )
        )

        return content

    async def close(self, dialog_id: str, reason: str = "completed"):
        """
        关闭对话

        Args:
            dialog_id: 对话 ID
            reason: 关闭原因
        """
        dialog = self._dialogs.pop(dialog_id, None)
        if dialog:
            self._event_bus.emit(DialogClosed(dialog_id=dialog_id, reason=reason))
            logger.info(f"[DialogManager] Closed dialog {dialog_id}, reason={reason}")

    def get_messages_for_llm(self, dialog_id: str) -> list[MessageDict]:
        """
        获取 LLM 格式的消息列表

        Args:
            dialog_id: 对话 ID

        Returns:
            OpenAI 格式的消息列表
        """
        dialog = self._get_dialog(dialog_id)
        return dialog.get_messages_for_llm()

    def _get_dialog(self, dialog_id: str) -> Dialog:
        """获取对话，不存在则抛出异常"""
        dialog = self._dialogs.get(dialog_id)
        if not dialog:
            raise ValueError(f"Dialog not found: {dialog_id}")
        return dialog

    async def compact_history(self, dialog_id: str) -> bool:
        """
        压缩对话历史 (当 token 数超过阈值时)

        Args:
            dialog_id: 对话 ID

        Returns:
            是否进行了压缩
        """
        dialog = self._get_dialog(dialog_id)

        if dialog.estimate_tokens() < self._token_threshold:
            return False

        # TODO: 实现压缩逻辑
        # 1. 提取关键信息
        # 2. 生成摘要
        # 3. 替换旧消息

        logger.info(f"[DialogManager] Compacted history for dialog {dialog_id}")
        return True
