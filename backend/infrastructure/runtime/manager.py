"""ManagerAwareRuntime - 带 Manager 集成的 Runtime 基类

提供完整的 Manager 初始化和生命周期管理。
适用于需要 DialogManager、ToolManager 等完整功能的 Runtime。
"""

from typing import Optional, Any, AsyncIterator, Callable
from abc import abstractmethod

from loguru import logger

from backend.infrastructure.runtime.runtime import AbstractAgentRuntime, ToolCache, ConfigT
from backend.infrastructure.runtime.mixins import ManagerLifecycleMixin
from backend.infrastructure.services.dialog_manager import DialogManager
from backend.infrastructure.services.tool_manager import ToolManager
from backend.infrastructure.services.state_manager import StateManager
from backend.infrastructure.services.provider_manager import ProviderManager
from backend.infrastructure.services.memory_manager import MemoryManager
from backend.infrastructure.services.skill_manager import SkillManager
from backend.domain.models.dialog import DialogSessionManager
from backend.domain.models.shared.config import EngineConfig
from backend.domain.models.dialog.dialog import Dialog
from backend.domain.models.agent.tool import ToolInfo
from backend.domain.models.shared import AgentEvent
from backend.infrastructure.runtime.event_bus import EventBus


class ManagerAwareRuntime(AbstractAgentRuntime[EngineConfig], ManagerLifecycleMixin):
    """
    带完整 Manager 集成的 Runtime 基类

    聚合所有标准 Managers，提供完整的 Agent 功能：
    - DialogManager: 对话管理
    - ToolManager: 工具管理
    - ProviderManager: LLM Provider 管理
    - MemoryManager: 长期记忆管理
    - SkillManager: 技能系统管理
    - StateManager: 状态持久化管理
    - EventBus: 事件总线

    子类只需实现消息处理逻辑 (send_message) 和停止逻辑 (stop)。

    Example:
        ```python
        class MyRuntime(ManagerAwareRuntime):
            @property
            def agent_type(self) -> str:
                return "my"

            async def send_message(self, dialog_id, message, stream=True):
                # 实现消息处理逻辑
                pass
        ```
    """

    def __init__(self, agent_id: str):
        super().__init__(agent_id)

        # 配置对象（子类特定）
        self._config_obj: Optional[EngineConfig] = None

        # 初始化基础设施
        self._event_bus = EventBus()

        # 初始化 Managers（在 _do_initialize 中重新配置）
        self._state_mgr = StateManager()
        self._provider_mgr = ProviderManager()
        self._dialog_mgr = DialogManager(
            event_bus=self._event_bus,
            state_manager=self._state_mgr
        )
        self._tool_mgr = ToolManager(event_bus=self._event_bus)
        self._memory_mgr = MemoryManager(event_bus=self._event_bus)
        self._skill_mgr = SkillManager(
            event_bus=self._event_bus,
            tool_manager=self._tool_mgr
        )

        # 初始化 SessionManager（新会话管理层）
        # 初始化 SessionManager（新会话管理层）
        self._session_mgr: Optional[DialogSessionManager] = None

        logger.debug(f"[{self.__class__.__name__}] Managers initialized")

    async def _initialize_managers(self, config: EngineConfig) -> None:
        """
        使用配置重新初始化所有 Managers

        Args:
            config: 引擎配置
        """
        self._config_obj = config

        # 重新初始化 Managers 并注入配置
        self._state_mgr = StateManager(config=config.state)
        self._provider_mgr = ProviderManager(config=config.provider)
        self._dialog_mgr = DialogManager(
            event_bus=self._event_bus,
            state_manager=self._state_mgr,
            config=config.dialog
        )
        self._tool_mgr = ToolManager(
            event_bus=self._event_bus,
            config=config.tools
        )
        self._memory_mgr = MemoryManager(
            event_bus=self._event_bus,
            config=config.memory
        )
        self._skill_mgr = SkillManager(
            event_bus=self._event_bus,
            tool_manager=self._tool_mgr,
            config=config.skills
        )

        logger.debug(f"[{self.__class__.__name__}] Managers configured")

    # ═══════════════════════════════════════════════════════════
    # 对话管理 - 基类已统一通过 DialogSessionManager 实现
    # ═══════════════════════════════════════════════════════════

    async def close_dialog(self, dialog_id: str, reason: str = "completed") -> None:
        """
        关闭对话

        Args:
            dialog_id: 对话 ID
            reason: 关闭原因
        """
        # 总结并写入 memory.md
        messages = self._dialog_mgr.get_messages_for_llm(dialog_id)
        provider = self._provider_mgr.default
        await self._memory_mgr.summarize_and_store(dialog_id, messages, provider)

        # 关闭 DialogManager 中的对话（遗留兼容）
        await self._dialog_mgr.close(dialog_id, reason)

    # ═══════════════════════════════════════════════════════════
    # 工具管理 - 集成 ToolManager 的版本
    # ═══════════════════════════════════════════════════════════

    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str,
        parameters_schema: Optional[dict[str, Any]] = None
    ) -> None:
        """
        注册工具（同时注册到 ToolManager 和本地缓存）

        Args:
            name: 工具名称
            handler: 工具处理函数
            description: 工具描述
            parameters_schema: 参数 JSON Schema
        """
        from backend.domain.models.shared.types import JSONSchema

        # 注册到 ToolManager
        json_schema: Optional[JSONSchema] = None
        if parameters_schema is not None:
            if isinstance(parameters_schema, dict):
                json_schema = JSONSchema(**parameters_schema)
            else:
                json_schema = parameters_schema  # type: ignore[assignment]

        self._tool_mgr.register(
            name=name,
            handler=handler,
            description=description,
            parameters=json_schema
        )

        # 更新本地缓存
        self._tools[name] = ToolCache(
            handler=handler,
            description=description,
            parameters_schema=parameters_schema or {}
        )

        logger.debug(f"[{self.__class__.__name__}] Registered tool: {name}")

    def unregister_tool(self, name: str) -> None:
        """
        注销工具（同时从 ToolManager 和本地缓存移除）

        Args:
            name: 工具名称
        """
        # 从 ToolManager 注销
        self._tool_mgr.unregister(name)

        # 从本地缓存移除
        self._tools.pop(name, None)

        logger.debug(f"[{self.__class__.__name__}] Unregistered tool: {name}")

    def list_tools(self) -> list[ToolInfo]:
        """
        列出可用工具

        Returns:
            ToolInfo 列表
        """
        return self._tool_mgr.list_available()

    # ═══════════════════════════════════════════════════════════
    # 技能管理
    # ═══════════════════════════════════════════════════════════

    def load_skill(self, skill_path: str) -> Optional[Any]:
        """加载技能"""
        return self._skill_mgr.load_skill_from_directory(skill_path)

    def list_skills(self) -> list[Any]:
        """列出所有技能"""
        return self._skill_mgr.list_skills()

    # ═══════════════════════════════════════════════════════════
    # 记忆管理
    # ═══════════════════════════════════════════════════════════

    def get_memory(self) -> str:
        """读取 memory.md 内容"""
        return self._memory_mgr.load_memory()

    # ═══════════════════════════════════════════════════════════
    # 事件管理
    # ═══════════════════════════════════════════════════════════

    def subscribe(
        self,
        callback: Callable,
        event_types: Optional[list[str]] = None,
        dialog_id: Optional[str] = None
    ) -> Callable:
        """订阅事件"""
        return self._event_bus.subscribe(callback, event_types, dialog_id)

    def emit(self, event: Any) -> None:
        """发射事件"""
        self._event_bus.emit(event)

    # ═══════════════════════════════════════════════════════════
    # SessionManager 集成 - 新的会话管理层
    # ═══════════════════════════════════════════════════════════

    @property
    def session_manager(self) -> Optional[DialogSessionManager]:
        """获取 SessionManager 实例"""
        return self._session_mgr

    def set_session_manager(self, session_manager: DialogSessionManager) -> None:
        """设置 SessionManager 实例（用于外部注入）"""
        self._session_mgr = session_manager
        logger.debug(f"[{self.__class__.__name__}] SessionManager set")

    async def create_session(self, dialog_id: str, title: Optional[str] = None) -> Any:
        """
        使用 SessionManager 创建新会话

        Args:
            dialog_id: 对话 ID
            title: 会话标题

        Returns:
            DialogSession 实例
        """
        if self._session_mgr is None:
            raise RuntimeError("SessionManager not initialized")
        return await self._session_mgr.create_session(dialog_id, title)

    async def get_session(self, dialog_id: str) -> Optional[Any]:
        """
        使用 SessionManager 获取会话

        Args:
            dialog_id: 对话 ID

        Returns:
            DialogSession 实例或 None
        """
        if self._session_mgr is None:
            return None
        return await self._session_mgr.get_session(dialog_id)

    async def close_session(self, dialog_id: str) -> None:
        """
        使用 SessionManager 关闭会话

        Args:
            dialog_id: 对话 ID
        """
        if self._session_mgr is None:
            return
        await self._session_mgr.close_session(dialog_id)

    # ═══════════════════════════════════════════════════════════
    # 抽象方法 - 子类必须实现
    # ═══════════════════════════════════════════════════════════

    @abstractmethod
    async def send_message(
        self,
        dialog_id: str,
        message: str,
        stream: bool = True
    ) -> AsyncIterator[AgentEvent]:
        """
        发送消息 - 子类实现

        Args:
            dialog_id: 对话 ID
            message: 消息内容
            stream: 是否流式返回

        Yields:
            AgentEvent: 流式事件
        """
        pass

    @abstractmethod
    async def stop(self, dialog_id: Optional[str] = None) -> None:
        """
        停止 Agent - 子类实现

        Args:
            dialog_id: 特定对话 ID（可选）
        """
        pass


__all__ = ["ManagerAwareRuntime"]