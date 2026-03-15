"""
BaseMonitoringBridge - 监控桥接器抽象基类

提供 Agent 与监控系统之间的桥接功能，实现 FullAgentHooks 接口，
将 Agent 生命周期事件转换为监控事件并发送到事件总线。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional
from uuid import UUID, uuid4
from loguru import logger

from ..domain.event import MonitoringEvent, EventType, EventPriority
from ..domain.payloads import (
    AgentStartedPayload,
    AgentStoppedPayload,
    AgentStoppedByUserPayload,
    AgentErrorPayload,
    MessageDeltaPayload,
    MessageCompletePayload,
    ToolCallStartPayload,
    ToolResultPayload,
    SubagentSpawnedPayload,
)
from ..services.event_bus import EventBus
from ..services.state_machine import StateMachine, AgentState
from ...base.abstract.hooks import FullAgentHooks


class IMonitoringBridge(ABC):
    """监控桥接器接口"""

    @abstractmethod
    def get_dialog_id(self) -> str:
        """获取对话框 ID"""
        raise NotImplementedError

    @abstractmethod
    def get_agent_name(self) -> str:
        """获取 Agent 名称"""
        raise NotImplementedError

    @abstractmethod
    def get_bridge_id(self) -> UUID:
        """获取桥接器唯一标识"""
        raise NotImplementedError

    @abstractmethod
    async def emit_event(self, event: MonitoringEvent) -> None:
        """发送监控事件"""
        raise NotImplementedError


class BaseMonitoringBridge(IMonitoringBridge, FullAgentHooks):
    """
    监控桥接器抽象基类

    实现 IMonitoringBridge 接口和 FullAgentHooks 接口，
    作为 Agent 和监控系统之间的桥梁，负责：
    - 将 Agent 生命周期事件转换为监控事件
    - 管理 Agent 状态机
    - 发送事件到事件总线

    Attributes:
        _dialog_id: 对话框 ID
        _agent_name: Agent 名称
        _bridge_id: 桥接器唯一标识
        _event_bus: 事件总线实例
        _state_machine: 状态机实例
        _parent: 父桥接器（用于子 Agent）
        _initialized: 是否已初始化
    """

    def __init__(
        self,
        dialog_id: str,
        agent_name: str,
        event_bus: EventBus,
        state_machine: Optional[StateMachine] = None,
        parent: Optional["BaseMonitoringBridge"] = None
    ):
        """
        初始化监控桥接器

        Args:
            dialog_id: 对话框 ID
            agent_name: Agent 名称
            event_bus: 事件总线实例
            state_machine: 可选的状态机实例，如果不提供则自动创建
            parent: 可选的父桥接器，用于子 Agent
        """
        self._dialog_id = dialog_id
        self._agent_name = agent_name
        self._bridge_id = uuid4()
        self._event_bus = event_bus
        self._state_machine = state_machine or StateMachine(dialog_id, event_bus)
        self._parent = parent
        self._initialized = False

        # 初始化状态转换规则
        self._setup_transitions()

    def _setup_transitions(self) -> None:
        """设置状态转换规则"""
        # 基本状态流转
        transitions = [
            (AgentState.IDLE, AgentState.INITIALIZING),
            (AgentState.INITIALIZING, AgentState.THINKING),
            (AgentState.THINKING, AgentState.TOOL_CALLING),
            (AgentState.THINKING, AgentState.SUBAGENT_RUNNING),
            (AgentState.THINKING, AgentState.COMPLETED),
            (AgentState.THINKING, AgentState.ERROR),
            (AgentState.TOOL_CALLING, AgentState.WAITING_FOR_TOOL),
            (AgentState.WAITING_FOR_TOOL, AgentState.THINKING),
            (AgentState.WAITING_FOR_TOOL, AgentState.ERROR),
            (AgentState.SUBAGENT_RUNNING, AgentState.THINKING),
            (AgentState.SUBAGENT_RUNNING, AgentState.COMPLETED),
            (AgentState.SUBAGENT_RUNNING, AgentState.ERROR),
            (AgentState.COMPLETED, AgentState.IDLE),
            (AgentState.ERROR, AgentState.IDLE),
            (AgentState.ERROR, AgentState.THINKING),
            (AgentState.PAUSED, AgentState.THINKING),
            (AgentState.THINKING, AgentState.PAUSED),
        ]

        for from_state, to_state in transitions:
            self._state_machine.add_transition(from_state, to_state)

    # =========================================================================
    # IMonitoringBridge 接口实现
    # =========================================================================

    def get_dialog_id(self) -> str:
        """获取对话框 ID"""
        return self._dialog_id

    def get_agent_name(self) -> str:
        """获取 Agent 名称"""
        return self._agent_name

    def get_bridge_id(self) -> UUID:
        """获取桥接器唯一标识"""
        return self._bridge_id

    async def emit_event(self, event: MonitoringEvent) -> None:
        """
        发送监控事件到事件总线

        Args:
            event: 要发送的监控事件
        """
        await self._event_bus.emit(event)

    # =========================================================================
    # 模板方法模式 - 初始化
    # =========================================================================

    def initialize(self) -> None:
        """
        初始化桥接器（模板方法）

        子类不应重写此方法，而应重写 _do_initialize() 方法。
        """
        if self._initialized:
            logger.warning(f"[BaseMonitoringBridge] Already initialized: {self._agent_name}")
            return

        try:
            self._do_initialize()
            self._initialized = True
            logger.info(f"[BaseMonitoringBridge] Initialized: {self._agent_name}")
        except Exception as e:
            logger.error(f"[BaseMonitoringBridge] Initialization failed: {e}")
            raise

    def _do_initialize(self) -> None:
        """
        子类实现的初始化逻辑

        子类应重写此方法以添加自定义初始化逻辑。
        """
        pass

    # =========================================================================
    # 受保护方法
    # =========================================================================

    def _emit(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        parent_event: Optional[MonitoringEvent] = None,
        priority: EventPriority = EventPriority.NORMAL
    ) -> MonitoringEvent:
        """
        创建并发送监控事件

        Args:
            event_type: 事件类型
            payload: 事件载荷
            parent_event: 可选的父事件，用于创建子事件
            priority: 事件优先级

        Returns:
            创建的监控事件
        """
        if parent_event:
            event = MonitoringEvent.create_child(
                parent=parent_event,
                type=event_type,
                payload=payload,
                priority=priority
            )
        else:
            event = MonitoringEvent(
                type=event_type,
                dialog_id=self._dialog_id,
                source=self._agent_name,
                context_id=self._bridge_id,
                priority=priority,
                payload=payload
            )

        # 使用 emit_sync 将事件放入队列（线程安全，非阻塞）
        self._event_bus.emit_sync(event)

        return event

    def _transition_state(self, state: AgentState, trigger: Optional[str] = None) -> None:
        """
        转换 Agent 状态

        Args:
            state: 目标状态
            trigger: 触发转换的事件/原因
        """
        import asyncio

        async def do_transition():
            success = await self._state_machine.transition(state, trigger=trigger)
            if not success:
                current = self._state_machine.get_current_state()
                logger.warning(
                    f"[BaseMonitoringBridge] State transition failed: "
                    f"{current.value} -> {state.value} (trigger={trigger})"
                )

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(do_transition())
            else:
                loop.run_until_complete(do_transition())
        except RuntimeError:
            asyncio.run(do_transition())

    # =========================================================================
    # FullAgentHooks 集成 - 钩子函数实现
    # =========================================================================

    def on_before_run(self, messages: list[dict[str, Any]]) -> None:
        """
        Agent 运行前钩子

        Args:
            messages: 消息列表
        """
        # 状态转换: INITIALIZING -> THINKING
        self._transition_state(AgentState.INITIALIZING, trigger="before_run")
        self._transition_state(AgentState.THINKING, trigger="start_processing")

        # 发送 AGENT_STARTED 事件
        agent_started_payload = AgentStartedPayload(
            agent_name=self._agent_name,
            bridge_id=str(self._bridge_id),
            message_count=len(messages),
            parent_bridge_id=str(self._parent._bridge_id) if self._parent else None
        )
        self._emit(
            EventType.AGENT_STARTED,
            payload=agent_started_payload.model_dump(),
            priority=EventPriority.CRITICAL
        )

        logger.debug(f"[BaseMonitoringBridge] on_before_run: {self._agent_name}")

    def on_stream_token(self, chunk: Any) -> None:
        """
        流式 Token 接收钩子

        Args:
            chunk: Token 块
        """
        # 状态保持: THINKING
        self._transition_state(AgentState.THINKING, trigger="stream_token")

        # 发送 MESSAGE_DELTA 事件
        chunk_content = ""
        if isinstance(chunk, str):
            chunk_content = chunk
        elif hasattr(chunk, "content"):
            chunk_content = chunk.content
        elif isinstance(chunk, dict):
            chunk_content = chunk.get("content", "")

        delta_payload = MessageDeltaPayload(
            agent_name=self._agent_name,
            chunk_type=type(chunk).__name__,
            delta=chunk_content  # 前端期望的字段名是 delta
        )
        self._emit(
            EventType.MESSAGE_DELTA,
            payload=delta_payload.model_dump(),
            priority=EventPriority.LOW
        )

    def on_tool_call(self, name: str, arguments: dict[str, Any], tool_call_id: str = "") -> None:
        """
        工具调用钩子

        Args:
            name: 工具名称
            arguments: 工具参数
            tool_call_id: 工具调用 ID
        """
        # 状态转换: THINKING -> TOOL_CALLING
        self._transition_state(AgentState.TOOL_CALLING, trigger=f"tool_call:{name}")

        # 发送 TOOL_CALL_START 事件
        tool_call_start_payload = ToolCallStartPayload(
            agent_name=self._agent_name,
            name=name,
            tool_call_id=tool_call_id,
            arguments=arguments
        )
        self._emit(
            EventType.TOOL_CALL_START,
            payload=tool_call_start_payload.model_dump(),
            priority=EventPriority.NORMAL
        )

        logger.debug(f"[BaseMonitoringBridge] on_tool_call: {name}")

    def on_tool_result(
        self,
        name: str,
        result: str,
        assistant_message: dict[str, Any] | None = None,
        tool_call_id: str = ""
    ) -> None:
        """
        工具结果钩子

        Args:
            name: 工具名称
            result: 工具结果
            assistant_message: 助手消息
            tool_call_id: 工具调用 ID
        """
        # 状态转换: WAITING_FOR_TOOL -> THINKING
        self._transition_state(AgentState.WAITING_FOR_TOOL, trigger="tool_result_received")
        self._transition_state(AgentState.THINKING, trigger="resume_thinking")

        # 发送 TOOL_RESULT 事件
        payload = ToolResultPayload(
            agent_name=self._agent_name,
            name=name,
            tool_call_id=tool_call_id,
            result=result,
            has_assistant_message=assistant_message is not None
        )
        self._emit(
            EventType.TOOL_RESULT,
            payload=payload.model_dump(),
            priority=EventPriority.HIGH
        )

        logger.debug(f"[BaseMonitoringBridge] on_tool_result: {name}")

    def on_complete(self, content: str) -> None:
        """
        Agent 完成钩子

        Args:
            content: 完成内容
        """
        # 状态转换: THINKING -> COMPLETED
        self._transition_state(AgentState.COMPLETED, trigger="generation_complete")

        # 发送 MESSAGE_COMPLETE 事件
        complete_payload = MessageCompletePayload(
            agent_name=self._agent_name,
            content_length=len(content),
            content_preview=content[:200] if content else ""
        )
        self._emit(
            EventType.MESSAGE_COMPLETE,
            payload=complete_payload.model_dump(),
            priority=EventPriority.HIGH
        )

        logger.debug(f"[BaseMonitoringBridge] on_complete: {self._agent_name}")

    def on_after_run(self, messages: list[dict[str, Any]], rounds: int) -> None:
        """
        Agent 运行后钩子

        Args:
            messages: 消息列表
            rounds: 运行轮数
        """
        # 状态保持或转换到 IDLE
        self._transition_state(AgentState.IDLE, trigger="run_complete")

        # 发送 AGENT_STOPPED 事件
        stopped_payload = AgentStoppedPayload(
            agent_name=self._agent_name,
            total_messages=len(messages),
            rounds=rounds,
            final_state=self._state_machine.get_current_state().value
        )
        self._emit(
            EventType.AGENT_STOPPED,
            payload=stopped_payload.model_dump(),
            priority=EventPriority.CRITICAL
        )

        logger.debug(f"[BaseMonitoringBridge] on_after_run: {self._agent_name}, rounds={rounds}")

    def on_error(self, error: Exception) -> None:
        """
        Agent 错误钩子

        Args:
            error: 异常对象
        """
        # 状态转换: 当前状态 -> ERROR
        self._transition_state(AgentState.ERROR, trigger=f"error:{type(error).__name__}")

        # 发送 AGENT_ERROR 事件
        error_payload = AgentErrorPayload(
            agent_name=self._agent_name,
            error_type=type(error).__name__,
            error_message=str(error),
            current_state=self._state_machine.get_current_state().value
        )
        self._emit(
            EventType.AGENT_ERROR,
            payload=error_payload.model_dump(),
            priority=EventPriority.CRITICAL
        )

        logger.error(f"[BaseMonitoringBridge] on_error: {self._agent_name}, error={error}")

    def on_stop(self) -> None:
        """Agent 停止钩子"""
        # 状态转换: 当前状态 -> IDLE
        self._transition_state(AgentState.IDLE, trigger="stopped")

        # 发送 AGENT_STOPPED 事件
        stopped_payload = AgentStoppedByUserPayload(
            agent_name=self._agent_name,
            reason="stopped_by_user",
            final_state=self._state_machine.get_current_state().value
        )
        self._emit(
            EventType.AGENT_STOPPED,
            payload=stopped_payload.model_dump(),
            priority=EventPriority.CRITICAL
        )

        logger.debug(f"[BaseMonitoringBridge] on_stop: {self._agent_name}")

    # =========================================================================
    # FullAgentHooks 集成 - 获取钩子函数字典
    # =========================================================================

    def get_hook_kwargs(self) -> dict[str, Any]:
        """
        获取所有钩子函数作为字典

        返回的字典可以直接传递给 Agent 的构造函数或配置。

        Returns:
            包含所有钩子函数的字典
        """
        return {
            "on_before_run": self.on_before_run,
            "on_stream_token": self.on_stream_token,
            "on_tool_call": self.on_tool_call,
            "on_tool_result": self.on_tool_result,
            "on_complete": self.on_complete,
            "on_after_run": self.on_after_run,
            "on_error": self.on_error,
            "on_stop": self.on_stop,
        }

    # =========================================================================
    # 工具方法
    # =========================================================================

    def is_initialized(self) -> bool:
        """检查桥接器是否已初始化"""
        return self._initialized

    def get_current_state(self) -> AgentState:
        """获取当前状态"""
        return self._state_machine.get_current_state()

    def get_state_history(self) -> list:
        """获取状态历史"""
        return self._state_machine.get_history()

    def create_child_bridge(self, child_agent_name: str) -> "BaseMonitoringBridge":
        """
        创建子桥接器

        用于子 Agent 的监控。

        Args:
            child_agent_name: 子 Agent 名称

        Returns:
            子桥接器实例
        """
        child_bridge = BaseMonitoringBridge(
            dialog_id=self._dialog_id,
            agent_name=child_agent_name,
            event_bus=self._event_bus,
            parent=self
        )

        # 发送 SUBAGENT_SPAWNED 事件
        spawned_payload = SubagentSpawnedPayload(
            parent_agent=self._agent_name,
            child_agent=child_agent_name,
            parent_bridge_id=str(self._bridge_id),
            child_bridge_id=str(child_bridge._bridge_id)
        )
        self._emit(
            EventType.SUBAGENT_SPAWNED,
            payload=spawned_payload.model_dump(),
            priority=EventPriority.HIGH
        )

        return child_bridge
