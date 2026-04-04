"""
Dialog Repository Interface - 对话仓库接口
"""

from abc import ABC, abstractmethod
from typing import Optional

from backend.domain.models import Dialog


class IDialogRepository(ABC):
    """对话仓库接口

    职责:
    - 定义对话持久化的抽象接口
    - 屏蔽底层存储实现细节
    - 支持同步和异步实现

    实现类:
    - InMemoryDialogRepository: 内存实现，用于测试和开发
    - FileDialogRepository: 文件持久化实现
    - DatabaseDialogRepository: 数据库持久化实现
    """

    @abstractmethod
    async def save(self, dialog: Dialog) -> None:
        """保存对话

        Args:
            dialog: 要保存的对话实体
        """
        pass

    @abstractmethod
    async def get(self, dialog_id: str) -> Optional[Dialog]:
        """获取对话

        Args:
            dialog_id: 对话 ID

        Returns:
            对话实体，如果不存在则返回 None
        """
        pass

    @abstractmethod
    async def list_all(self) -> list[Dialog]:
        """列出所有对话

        Returns:
            所有对话实体的列表
        """
        pass

    @abstractmethod
    async def delete(self, dialog_id: str) -> None:
        """删除对话

        Args:
            dialog_id: 要删除的对话 ID
        """
        pass
