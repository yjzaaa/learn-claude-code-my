"""Capabilities Layer Interfaces - 领域能力层接口

第2层：领域能力层暴露的抽象接口
运行时层通过此模块依赖能力层，不感知具体实现。
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class DialogSnapshot(BaseModel):
    """对话快照"""

    dialog_id: str
    title: str
    messages: list[BaseModel]


class IDialogManager(ABC):
    """对话管理器接口（能力层抽象）"""

    @abstractmethod
    async def create(self, user_input: str, title: str | None = None) -> str:
        """
        创建新对话

        Args:
            user_input: 用户初始输入
            title: 对话标题（可选）

        Returns:
            新创建的对话 ID
        """
        pass

    @abstractmethod
    def get(self, dialog_id: str) -> DialogSnapshot | None:
        """
        获取对话

        Args:
            dialog_id: 对话 ID

        Returns:
            DialogSnapshot 或 None
        """
        pass

    @abstractmethod
    def list_dialogs(self) -> list[DialogSnapshot]:
        """
        列出所有对话

        Returns:
            DialogSnapshot 列表
        """
        pass

    @abstractmethod
    def get_messages_for_llm(self, dialog_id: str) -> list[BaseModel]:
        """
        获取用于 LLM 的消息列表

        Args:
            dialog_id: 对话 ID

        Returns:
            消息列表（Pydantic BaseModel）
        """
        pass

    @abstractmethod
    async def add_user_message(self, dialog_id: str, content: str) -> None:
        """
        添加用户消息

        Args:
            dialog_id: 对话 ID
            content: 消息内容
        """
        pass

    @abstractmethod
    async def add_assistant_message(self, dialog_id: str, content: str) -> None:
        """
        添加助手消息

        Args:
            dialog_id: 对话 ID
            content: 消息内容
        """
        pass

    @abstractmethod
    async def close(self, dialog_id: str, reason: str = "completed") -> None:
        """
        关闭对话

        Args:
            dialog_id: 对话 ID
            reason: 关闭原因
        """
        pass


class IToolManager(ABC):
    """工具管理器接口"""

    @abstractmethod
    def register(
        self,
        name: str,
        handler: Any,
        description: str,
        parameters: BaseModel | None = None,
    ) -> None:
        """
        注册工具

        Args:
            name: 工具名称
            handler: 处理函数
            description: 工具描述
            parameters: 参数 Schema（Pydantic BaseModel）
        """
        pass

    @abstractmethod
    def unregister(self, name: str) -> None:
        """
        注销工具

        Args:
            name: 工具名称
        """
        pass

    @abstractmethod
    def get_schemas(self) -> list[BaseModel]:
        """
        获取所有工具 Schema

        Returns:
            工具 Schema 列表（Pydantic BaseModel）
        """
        pass

    @abstractmethod
    async def execute(self, dialog_id: str, tool_call: BaseModel) -> str:
        """
        执行工具调用

        Args:
            dialog_id: 对话 ID
            tool_call: 工具调用（Pydantic BaseModel）

        Returns:
            执行结果字符串
        """
        pass


class ISkillManager(ABC):
    """技能管理器接口"""

    @abstractmethod
    def list_skills(self) -> list[BaseModel]:
        """
        列出所有技能

        Returns:
            技能列表（Pydantic BaseModel）
        """
        pass

    @abstractmethod
    def get_skill_prompt(self, skill_id: str) -> str | None:
        """
        获取技能 Prompt

        Args:
            skill_id: 技能 ID

        Returns:
            Prompt 字符串或 None
        """
        pass

    @abstractmethod
    def load_builtin_skills(self) -> None:
        """加载内置技能"""
        pass


class IMemoryManager(ABC):
    """记忆管理器接口"""

    @abstractmethod
    def load_memory(self) -> str:
        """
        加载记忆

        Returns:
            记忆内容字符串
        """
        pass

    @abstractmethod
    async def summarize_and_store(
        self,
        dialog_id: str,
        messages: list[BaseModel],
        provider: Any,
    ) -> None:
        """
        总结并存储记忆

        Args:
            dialog_id: 对话 ID
            messages: 消息列表（Pydantic BaseModel）
            provider: LLM Provider
        """
        pass


__all__ = [
    "IDialogManager",
    "IToolManager",
    "ISkillManager",
    "IMemoryManager",
    "DialogSnapshot",
]
