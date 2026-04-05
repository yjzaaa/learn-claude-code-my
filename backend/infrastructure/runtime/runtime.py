"""
AbstractAgentRuntime - Runtime 抽象基类

提供 AgentRuntime 的通用实现，使用模板方法模式。
子类只需实现特定的初始化、消息处理和停止逻辑。
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any, Callable, AsyncIterator, Optional, Dict, List, Union
from datetime import datetime
import uuid

from loguru import logger
from pydantic import BaseModel, Field

from backend.domain.models.dialog.dialog import Dialog
from backend.domain.models.events.agent import AgentEvent


ConfigT = TypeVar("ConfigT", bound=BaseModel)


class ToolCache(BaseModel):
    """
    工具缓存模型 - 统一所有 Runtime 的工具存储

    Attributes:
        handler: 工具处理函数
        description: 工具描述
        parameters_schema: JSON Schema 参数定义
    """

    handler: Any = None
    description: str = ""
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class AbstractAgentRuntime(Generic[ConfigT], ABC):
    """
    Agent Runtime 抽象基类

    提供通用实现，使用模板方法模式分离通用逻辑和特定逻辑：
    - 通用: 配置验证、工具缓存、对话管理、日志记录
    - 特定: 初始化逻辑、消息处理、停止逻辑 (子类实现)

    Type Parameters:
        ConfigT: 配置类型，必须是 BaseModel 子类

    Example:
        ```python
        class SimpleRuntime(AbstractAgentRuntime[EngineConfig]):
            @property
            def agent_type(self) -> str:
                return "simple"

            async def _do_initialize(self) -> None:
                # 初始化特定组件
                self._state_mgr = StateManager()
        ```
    """

    def __init__(self, agent_id: str):
        """
        初始化抽象基类

        Args:
            agent_id: 运行时唯一标识
        """
        self._agent_id = agent_id
        self._config: Optional[ConfigT] = None
        self._tools: Dict[str, ToolCache] = {}

        logger.debug(f"[{self.__class__.__name__}] Created: {agent_id}")

    @property
    def runtime_id(self) -> str:
        """运行时唯一标识"""
        return self._agent_id

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """
        Agent 类型标识

        Returns:
            类型字符串，如 "simple", "deep"
        """
        pass

    @property
    @abstractmethod
    def session_manager(self) -> Optional[Any]:
        """
        获取 SessionManager 实例

        Returns:
            DialogSessionManager 实例或 None
        """
        pass

    def _validate_config(self, config: Union[ConfigT, Dict[str, Any]]) -> ConfigT:
        """
        验证并转换配置

        子类可覆盖此方法来提供自定义验证逻辑。

        Args:
            config: 配置对象或字典

        Returns:
            验证后的配置对象
        """
        if isinstance(config, dict):
            # 子类需要指定具体的 Config 类进行验证
            raise NotImplementedError(
                "Subclass must implement _validate_config to handle dict input"
            )
        return config

    async def initialize(self, config: Union[ConfigT, Dict[str, Any]]) -> None:  # type: ignore[override]
        """
        初始化 Runtime - 模板方法

        执行流程:
        1. 验证配置 (_validate_config)
        2. 子类特定初始化 (_do_initialize)
        3. 记录初始化日志

        Args:
            config: 配置对象或字典
        """
        # 验证配置
        if isinstance(config, dict):
            self._config = self._validate_config(config)
        else:
            self._config = config

        # 子类特定初始化
        await self._do_initialize()

        logger.info(f"[{self.__class__.__name__}] Initialized: {self._agent_id}")

    @abstractmethod
    async def _do_initialize(self) -> None:
        """
        子类实现: 特定初始化逻辑

        在此方法中完成 Runtime 特定的初始化工作，如:
        - 初始化 Managers
        - 创建底层 Agent 实例
        - 加载技能/插件
        """
        pass

    async def shutdown(self) -> None:
        """
        关闭 Runtime - 模板方法

        执行流程:
        1. 子类特定清理 (_do_shutdown)
        2. 记录关闭日志
        """
        # 子类特定清理
        await self._do_shutdown()

        logger.info(f"[{self.__class__.__name__}] Shutdown: {self._agent_id}")

    @abstractmethod
    async def _do_shutdown(self) -> None:
        """
        子类实现: 特定清理逻辑

        在此方法中完成 Runtime 特定的清理工作，如:
        - 保存状态
        - 关闭连接
        - 释放资源
        """
        pass

    @abstractmethod
    async def send_message(
        self,
        dialog_id: str,
        message: str,
        stream: bool = True,
        message_id: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]:
        """
        发送消息到 Agent - 子类实现

        Args:
            dialog_id: 对话 ID
            message: 消息内容
            stream: 是否流式返回
            message_id: 消息 ID（用于与流式占位符对齐）

        Yields:
            AgentEvent: 流式事件
        """
        pass

    async def create_dialog(self, user_input: str, title: Optional[str] = None) -> str:
        """
        创建新对话（仅通过 DialogSessionManager）

        Args:
            user_input: 用户初始输入
            title: 对话标题（可选）

        Returns:
            新创建的对话 ID
        """
        dialog_id = str(uuid.uuid4())

        dialog_title = title if title else (
            user_input[:50] + "..." if len(user_input) > 50 else user_input
        )

        session_mgr = self.session_manager
        if session_mgr is None:
            raise RuntimeError("SessionManager not set. Cannot create dialog without session manager.")

        await session_mgr.create_session(dialog_id, title=dialog_title)
        if user_input:
            await session_mgr.add_user_message(dialog_id, user_input)

        logger.info(f"[{self.__class__.__name__}] Created dialog: {dialog_id}")
        return dialog_id

    def get_dialog(self, dialog_id: str) -> Optional[Dialog]:
        """
        获取对话（通过 DialogSessionManager）

        Args:
            dialog_id: 对话 ID

        Returns:
            Dialog 对象或 None
        """
        session_mgr = self.session_manager
        if session_mgr is None:
            return None
        session = session_mgr.get_session_sync(dialog_id)
        if session is None:
            return None
        return Dialog(
            id=session.dialog_id,
            title=session.metadata.title or "New Dialog",
            messages=list(session.history.messages),
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def list_dialogs(self) -> List[Dialog]:
        """
        列出所有对话（通过 DialogSessionManager）

        Returns:
            Dialog 列表
        """
        session_mgr = self.session_manager
        if session_mgr is None:
            return []
        dialogs = []
        for session in session_mgr.list_sessions():
            dialogs.append(Dialog(
                id=session.dialog_id,
                title=session.metadata.title or "New Dialog",
                messages=list(session.history.messages),
                created_at=session.created_at,
                updated_at=session.updated_at,
            ))
        return dialogs

    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str,
        parameters_schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        注册工具

        Args:
            name: 工具名称
            handler: 工具处理函数
            description: 工具描述
            parameters_schema: 参数 JSON Schema
        """
        self._tools[name] = ToolCache(
            handler=handler,
            description=description,
            parameters_schema=parameters_schema or {}
        )
        logger.debug(f"[{self.__class__.__name__}] Registered tool: {name}")

    def unregister_tool(self, name: str) -> None:
        """
        注销工具

        Args:
            name: 工具名称
        """
        if name in self._tools:
            del self._tools[name]
            logger.debug(f"[{self.__class__.__name__}] Unregistered tool: {name}")

    @abstractmethod
    async def stop(self, dialog_id: Optional[str] = None) -> None:
        """
        停止 Agent - 子类实现

        Args:
            dialog_id: 特定对话 ID（可选，为 None 则停止所有）
        """
        pass


__all__ = ["AbstractAgentRuntime", "ToolCache", "ConfigT"]
