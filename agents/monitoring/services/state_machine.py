"""
StateMachine - 状态机服务

提供 Agent 状态管理和转换功能。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from loguru import logger

try:
    from ..domain import AgentState, StateTransition
    from ..domain.transitions import STANDARD_TRANSITIONS, STANDARD_TRANSITION_COUNT
except ImportError:
    from agents.monitoring.domain import AgentState, StateTransition
    from agents.monitoring.domain.transitions import STANDARD_TRANSITIONS, STANDARD_TRANSITION_COUNT


class StateMachine:
    """管理 Agent 状态，支持转换守卫、历史记录和回调。"""

    def __init__(self, dialog_id: str, event_bus: Optional[Any] = None):
        """初始化状态机"""
        self._dialog_id = dialog_id
        self._event_bus = event_bus
        self._current_state = AgentState.IDLE
        self._history: List[StateTransition] = []
        self._entered_at = datetime.utcnow()
        self._lock = asyncio.Lock()

        # 转换规则: (from_state, to_state) -> {guards: [], on_transition: []}
        self._transitions: Dict[
            Tuple[AgentState, AgentState],
            Dict[str, List[Callable]]
        ] = {}

        # 进入/退出回调: state -> [callbacks]
        self._on_enter: Dict[AgentState, List[Callable]] = {}
        self._on_exit: Dict[AgentState, List[Callable]] = {}

        # 初始化标准状态转换图
        self._init_standard_transitions()

    def _init_standard_transitions(self) -> None:
        """初始化标准 Agent 状态转换图"""
        for from_state, to_state in STANDARD_TRANSITIONS:
            self.add_transition(from_state, to_state)
        logger.debug(f"[StateMachine] Initialized {STANDARD_TRANSITION_COUNT} standard transitions")

    def add_transition(
        self,
        from_state: AgentState,
        to_state: AgentState,
        guard: Optional[Callable[[], bool]] = None,
        on_transition: Optional[Callable[[AgentState, AgentState], None]] = None
    ) -> None:
        """添加状态转换规则"""
        key = (from_state, to_state)
        if key not in self._transitions:
            self._transitions[key] = {"guards": [], "on_transition": []}

        if guard:
            self._transitions[key]["guards"].append(guard)

        if on_transition:
            self._transitions[key]["on_transition"].append(on_transition)

        logger.debug(f"[StateMachine] Transition added: {from_state.value} -> {to_state.value}")

    def on_enter(self, state: AgentState, callback: Callable[[AgentState], None]) -> None:
        """注册进入状态回调"""
        if state not in self._on_enter:
            self._on_enter[state] = []
        self._on_enter[state].append(callback)

    def on_exit(self, state: AgentState, callback: Callable[[AgentState], None]) -> None:
        """注册退出状态回调"""
        if state not in self._on_exit:
            self._on_exit[state] = []
        self._on_exit[state].append(callback)

    async def transition(self, to_state: AgentState, trigger: Optional[str] = None) -> bool:
        """执行状态转换，返回 True 如果成功"""
        async with self._lock:
            from_state = self._current_state

            # 检查是否有转换规则
            key = (from_state, to_state)
            if key not in self._transitions:
                logger.warning(
                    f"[StateMachine] No transition rule: {from_state.value} -> {to_state.value}"
                )
                return False

            transition_config = self._transitions[key]

            # 检查守卫条件
            for guard in transition_config.get("guards", []):
                try:
                    if asyncio.iscoroutinefunction(guard):
                        result = await guard()
                    else:
                        result = guard()

                    if not result:
                        logger.debug(
                            f"[StateMachine] Transition guard rejected: {from_state.value} -> {to_state.value}"
                        )
                        return False
                except Exception as e:
                    logger.error(f"[StateMachine] Guard error: {e}")
                    return False

            # 计算在源状态的持续时间
            duration_ms = int(
                (datetime.utcnow() - self._entered_at).total_seconds() * 1000
            )

            # 执行退出回调
            for callback in self._on_exit.get(from_state, []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(to_state)
                    else:
                        callback(to_state)
                except Exception as e:
                    logger.error(f"[StateMachine] Exit callback error: {e}")

            # 执行转换回调
            for callback in transition_config.get("on_transition", []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(from_state, to_state)
                    else:
                        callback(from_state, to_state)
                except Exception as e:
                    logger.error(f"[StateMachine] Transition callback error: {e}")

            # 记录转换
            transition_record = StateTransition(
                from_state=from_state,
                to_state=to_state,
                trigger=trigger,
                duration_ms=duration_ms,
                guard_result=True
            )
            self._history.append(transition_record)

            # 更新状态
            self._current_state = to_state
            self._entered_at = datetime.utcnow()

            # 广播状态变更事件（如果有 event_bus）
            if self._event_bus:
                from ..domain.event import MonitoringEvent, EventType
                from ..domain.payloads import StateTransitionPayload
                payload = StateTransitionPayload(
                    from_state=from_state.value,
                    to_state=to_state.value,
                    trigger=trigger,
                    duration_ms=duration_ms
                )
                event = MonitoringEvent(
                    type=EventType.STATE_TRANSITION,
                    dialog_id=self._dialog_id,
                    source="StateMachine",
                    context_id=__import__('uuid').uuid4(),
                    payload=payload.model_dump()
                )
                await self._event_bus.emit(event)

            # 执行进入回调
            for callback in self._on_enter.get(to_state, []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(from_state)
                    else:
                        callback(from_state)
                except Exception as e:
                    logger.error(f"[StateMachine] Enter callback error: {e}")

            logger.info(
                f"[StateMachine] Transition: {from_state.value} -> {to_state.value} "
                f"(trigger={trigger}, duration={duration_ms}ms)"
            )

            return True

    def can_transition(self, to_state: AgentState) -> bool:
        """
        检查是否可以转换到指定状态

        不执行实际转换，只检查规则是否存在且守卫通过。

        Args:
            to_state: 目标状态

        Returns:
            True 如果可以转换
        """
        key = (self._current_state, to_state)
        if key not in self._transitions:
            return False

        # 检查守卫条件（非阻塞）
        for guard in self._transitions[key].get("guards", []):
            try:
                if asyncio.iscoroutinefunction(guard):
                    # 异步守卫无法非阻塞检查，默认通过
                    continue
                if not guard():
                    return False
            except Exception:
                return False

        return True

    def get_current_state(self) -> AgentState:
        """获取当前状态"""
        return self._current_state

    def get_history(self) -> List[StateTransition]:
        """获取状态转换历史"""
        return list(self._history)

    def get_time_in_state_ms(self) -> int:
        """获取在当前状态的持续时间（毫秒）"""
        return int(
            (datetime.utcnow() - self._entered_at).total_seconds() * 1000
        )

    def get_allowed_transitions(self) -> Set[AgentState]:
        """获取所有允许的目标状态"""
        allowed = set()
        for (from_state, to_state) in self._transitions.keys():
            if from_state == self._current_state:
                allowed.add(to_state)
        return allowed

    def reset(self) -> None:
        """重置状态机到初始状态"""
        self._current_state = AgentState.IDLE
        self._history.clear()
        self._entered_at = datetime.utcnow()
        logger.debug("[StateMachine] Reset to IDLE")
