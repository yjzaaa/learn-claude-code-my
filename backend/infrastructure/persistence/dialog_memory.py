"""
In-Memory Dialog Repository - 内存对话仓库实现
"""

from typing import Optional

from backend.domain.repositories.dialog_repository import IDialogRepository
from backend.domain.models import Dialog


class InMemoryDialogRepository(IDialogRepository):
    """内存对话仓库实现

    使用字典存储对话，适用于:
    - 开发和测试环境
    - 单进程部署
    - 不需要持久化的场景

    注意: 进程重启后数据丢失
    """

    def __init__(self):
        self._dialogs: dict[str, Dialog] = {}

    async def save(self, dialog: Dialog) -> None:
        """保存对话到内存

        Args:
            dialog: 要保存的对话实体
        """
        self._dialogs[dialog.id] = dialog

    async def get(self, dialog_id: str) -> Optional[Dialog]:
        """从内存获取对话

        Args:
            dialog_id: 对话 ID

        Returns:
            对话实体，如果不存在则返回 None
        """
        return self._dialogs.get(dialog_id)

    async def list_all(self) -> list[Dialog]:
        """列出内存中所有对话

        Returns:
            所有对话实体的列表
        """
        return list(self._dialogs.values())

    async def delete(self, dialog_id: str) -> None:
        """从内存删除对话

        Args:
            dialog_id: 要删除的对话 ID
        """
        self._dialogs.pop(dialog_id, None)

    def clear(self) -> None:
        """清空所有对话 (仅用于测试)"""
        self._dialogs.clear()

    def count(self) -> int:
        """获取对话数量 (仅用于测试)"""
        return len(self._dialogs)
