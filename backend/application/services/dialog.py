"""
DialogService - 对话应用服务

职责:
- 编排对话生命周期用例
- 协调 Dialog, Message, Runtime
- 不直接操作底层存储，通过 Repository

与 DialogManager 区别:
- DialogManager: 底层管理，直接操作内存/存储
- DialogService: 高层编排，面向用例
"""

from typing import AsyncIterator, Optional
from datetime import datetime

from backend.domain.models import Dialog
from backend.application.dto.responses import (
    CreateDialogResult,
    SendMessageResult,
    MessageDTO,
)
from backend.domain.models.events import (
    DialogCreated,
    MessageReceived,
    MessageCompleted,
    DialogClosed,
)


class DialogNotFoundError(Exception):
    """对话不存在错误"""
    pass


class DialogService:
    """对话应用服务

    提供对话生命周期管理的高级用例接口，
    协调多个领域对象完成业务用例。

    Attributes:
        _repo: 对话仓库接口
        _event_bus: 事件总线接口
        _runtime: Agent 运行时接口
    """

    def __init__(
        self,
        dialog_repo,
        event_bus,
        runtime,
    ):
        """初始化 DialogService

        Args:
            dialog_repo: 实现 IDialogRepository 接口的对象
            event_bus: 实现 IEventBus 接口的对象
            runtime: 实现 IAgentRuntime 接口的对象
        """
        self._repo = dialog_repo
        self._event_bus = event_bus
        self._runtime = runtime

    async def create_dialog(
        self,
        user_input: str,
        title: Optional[str] = None
    ) -> CreateDialogResult:
        """创建对话用例

        流程:
        1. 创建 Dialog 实体
        2. 添加用户消息
        3. 保存到 Repository
        4. 发射领域事件

        Args:
            user_input: 用户初始输入
            title: 对话标题（可选，默认取输入前50字符）

        Returns:
            CreateDialogResult: 创建结果
        """
        # 1. 创建领域对象
        dialog = Dialog.from_user_input(user_input)
        if title:
            dialog.title = title

        # 2. 持久化
        await self._repo.save(dialog)

        # 3. 发射事件
        self._event_bus.emit(DialogCreated(
            dialog_id=dialog.id,
            user_input=user_input,
        ))

        return CreateDialogResult(
            dialog_id=dialog.id,
            title=dialog.title or "New Dialog",
            created_at=dialog.created_at.isoformat()
        )

    async def send_message(
        self,
        dialog_id: str,
        content: str,
        stream: bool = True
    ) -> AsyncIterator[str]:
        """发送消息用例

        流程:
        1. 获取对话
        2. 添加用户消息
        3. 调用 Runtime 生成回复
        4. 流式返回内容
        5. 保存助手消息

        Args:
            dialog_id: 对话 ID
            content: 消息内容
            stream: 是否流式返回（默认 True）

        Yields:
            str: 流式内容块

        Raises:
            DialogNotFoundError: 对话不存在时
        """
        # 1. 获取对话
        dialog = await self._repo.get(dialog_id)
        if not dialog:
            raise DialogNotFoundError(f"Dialog not found: {dialog_id}")

        # 2. 添加用户消息
        user_msg = dialog.add_human_message(content)
        await self._repo.save(dialog)

        # 3. 发射事件
        self._event_bus.emit(MessageReceived(
            dialog_id=dialog_id,
            message_id=user_msg.id if hasattr(user_msg, 'id') else "",
            content=content,
        ))

        # 4. 调用 Runtime 生成回复
        full_content = []
        async for event in self._runtime.send_message(dialog_id, content, stream=stream):
            if hasattr(event, 'data') and event.data:
                chunk = str(event.data)
                full_content.append(chunk)
                if stream:
                    yield chunk

        # 5. 保存助手消息
        assistant_content = "".join(full_content)
        if assistant_content:
            assistant_msg = dialog.add_ai_message(assistant_content)
            await self._repo.save(dialog)

            # 6. 发射完成事件
            self._event_bus.emit(MessageCompleted(
                dialog_id=dialog_id,
                message_id=assistant_msg.id if hasattr(assistant_msg, 'id') else "",
                content=assistant_content,
                token_count=dialog.estimate_tokens(),
            ))

    async def get_dialog_history(
        self,
        dialog_id: str,
        limit: int = 100
    ) -> list[MessageDTO]:
        """获取对话历史

        Args:
            dialog_id: 对话 ID
            limit: 返回消息数量上限（默认 100）

        Returns:
            list[MessageDTO]: 消息 DTO 列表

        Raises:
            DialogNotFoundError: 对话不存在时
        """
        dialog = await self._repo.get(dialog_id)
        if not dialog:
            raise DialogNotFoundError(f"Dialog not found: {dialog_id}")

        messages = dialog.messages[-limit:] if limit > 0 else dialog.messages
        return [MessageDTO.from_entity(m) for m in messages]

    async def close_dialog(self, dialog_id: str) -> None:
        """关闭对话

        Args:
            dialog_id: 对话 ID

        Raises:
            DialogNotFoundError: 对话不存在时
        """
        dialog = await self._repo.get(dialog_id)
        if not dialog:
            raise DialogNotFoundError(f"Dialog not found: {dialog_id}")

        # 标记对话为关闭状态（可以扩展 Dialog 实体添加状态字段）
        await self._repo.save(dialog)

        self._event_bus.emit(DialogClosed(
            dialog_id=dialog_id,
            reason="completed",
        ))

    async def get_dialog(self, dialog_id: str) -> Optional[Dialog]:
        """获取对话实体

        Args:
            dialog_id: 对话 ID

        Returns:
            Dialog: 对话实体，不存在时返回 None
        """
        return await self._repo.get(dialog_id)

    async def list_dialogs(self) -> list[Dialog]:
        """列出所有对话

        Returns:
            list[Dialog]: 对话实体列表
        """
        return await self._repo.list_all()
