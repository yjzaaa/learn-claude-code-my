"""
CompositeMonitoringBridge - 组合监控桥接器

实现 Composite 模式，用于管理子智能体和后台任务的监控。
包含三个主要类：
- ChildMonitoringBridge: 子智能体监控桥接器
- BackgroundTaskBridge: 后台任务监控桥接器
- CompositeMonitoringBridge: 组合桥接器，管理多个子桥接器
"""

from __future__ import annotations

import asyncio
import subprocess
import threading
from typing import Any, Optional
from uuid import UUID, uuid4
from datetime import datetime

from loguru import logger

from ..domain.event import MonitoringEvent, EventType, EventPriority
from ..domain.payloads import (
    SubagentStartedWithBridgePayload,
    SubagentProgressWithBridgePayload,
    SubagentCompletedWithBridgePayload,
    SubagentFailedWithBridgePayload,
    SubagentSpawnedWithParentPayload,
    BgTaskQueuedPayload,
    BgTaskStartedPayload,
    BgTaskProgressPayload,
    BgTaskCompletedWithBridgePayload,
    BgTaskFailedWithExitCodePayload,
)
from ..services.event_bus import EventBus, event_bus
from ..services.state_machine import StateMachine, AgentState
from .base import BaseMonitoringBridge, IMonitoringBridge


class ChildMonitoringBridge(BaseMonitoringBridge):
    """
    子智能体监控桥接器

    用于监控子智能体的执行过程，继承自 BaseMonitoringBridge。

    Attributes:
        _subagent_type: 子智能体类型标识
        _subagent_name: 子智能体名称
        _parent_bridge_id: 父桥接器 ID
    """

    def __init__(
        self,
        dialog_id: str,
        subagent_name: str,
        subagent_type: str,
        event_bus: EventBus,
        parent_bridge_id: UUID,
        state_machine: Optional[StateMachine] = None
    ):
        """
        初始化子智能体监控桥接器

        Args:
            dialog_id: 对话标识
            subagent_name: 子智能体名称
            subagent_type: 子智能体类型标识
            event_bus: 事件总线
            parent_bridge_id: 父桥接器 ID
            state_machine: 可选的状态机
        """
        super().__init__(
            dialog_id=dialog_id,
            agent_name=f"Subagent:{subagent_name}",
            event_bus=event_bus,
            state_machine=state_machine
        )
        self._subagent_name: str = subagent_name
        self._subagent_type: str = subagent_type
        self._parent_bridge_id: UUID = parent_bridge_id
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._subagent_status: str = "initialized"  # initialized, running, completed, failed

    @property
    def subagent_type(self) -> str:
        """子智能体类型"""
        return self._subagent_type

    @property
    def subagent_name(self) -> str:
        """子智能体名称"""
        return self._subagent_name

    @property
    def parent_bridge_id(self) -> UUID:
        """父桥接器 ID"""
        return self._parent_bridge_id

    @property
    def subagent_status(self) -> str:
        """当前状态"""
        return self._subagent_status

    def _do_initialize(self) -> None:
        """子类初始化逻辑"""
        self._setup_transitions()

    def mark_started(self) -> MonitoringEvent:
        """
        标记子智能体开始执行

        Returns:
            生成的事件
        """
        self._subagent_status = "running"
        self._started_at = datetime.utcnow()
        self._transition_state(AgentState.THINKING, trigger="subagent_started")
        payload = SubagentStartedWithBridgePayload(
            subagent_name=self._subagent_name,
            subagent_type=self._subagent_type,
            parent_bridge_id=str(self._parent_bridge_id),
            bridge_id=str(self._bridge_id)
        )
        return self._emit(
            EventType.SUBAGENT_STARTED,
            payload=payload.model_dump(),
            priority=EventPriority.HIGH
        )

    def mark_progress(self, progress_data: dict[str, Any]) -> MonitoringEvent:
        """
        报告子智能体进度

        Args:
            progress_data: 进度数据

        Returns:
            生成的事件
        """
        payload = SubagentProgressWithBridgePayload(
            subagent_name=self._subagent_name,
            subagent_type=self._subagent_type,
            progress=progress_data,
            bridge_id=str(self._bridge_id)
        )
        return self._emit(
            EventType.SUBAGENT_PROGRESS,
            payload=payload.model_dump(),
            priority=EventPriority.LOW
        )

    def mark_completed(self, result: Optional[dict[str, Any]] = None) -> MonitoringEvent:
        """
        标记子智能体完成

        Args:
            result: 执行结果数据

        Returns:
            生成的事件
        """
        self._subagent_status = "completed"
        self._completed_at = datetime.utcnow()
        self._transition_state(AgentState.COMPLETED, trigger="subagent_completed")

        duration_ms = 0
        if self._started_at:
            duration_ms = int((self._completed_at - self._started_at).total_seconds() * 1000)

        payload = SubagentCompletedWithBridgePayload(
            subagent_name=self._subagent_name,
            subagent_type=self._subagent_type,
            result=result or {},
            duration_ms=duration_ms,
            bridge_id=str(self._bridge_id)
        )
        return self._emit(
            EventType.SUBAGENT_COMPLETED,
            payload=payload.model_dump(),
            priority=EventPriority.HIGH
        )

    def mark_failed(self, error: str) -> MonitoringEvent:
        """
        标记子智能体失败

        Args:
            error: 错误信息

        Returns:
            生成的事件
        """
        self._subagent_status = "failed"
        self._completed_at = datetime.utcnow()
        self._transition_state(AgentState.ERROR, trigger="subagent_failed")
        payload = SubagentFailedWithBridgePayload(
            subagent_name=self._subagent_name,
            subagent_type=self._subagent_type,
            error=error,
            bridge_id=str(self._bridge_id)
        )
        return self._emit(
            EventType.SUBAGENT_FAILED,
            payload=payload.model_dump(),
            priority=EventPriority.CRITICAL
        )


class BackgroundTaskBridge(BaseMonitoringBridge):
    """
    后台任务监控桥接器

    用于监控后台命令执行，支持实时输出流。

    Attributes:
        _task_id: 任务唯一标识
        _command: 执行的命令
        _process: 子进程对象
        _output_buffer: 输出缓冲区
        _status: 任务状态
    """

    def __init__(
        self,
        dialog_id: str,
        task_id: str,
        command: str,
        event_bus: EventBus,
        state_machine: Optional[StateMachine] = None
    ):
        """
        初始化后台任务监控桥接器

        Args:
            dialog_id: 对话标识
            task_id: 任务唯一标识
            command: 执行的命令
            event_bus: 事件总线
            state_machine: 可选的状态机
        """
        super().__init__(
            dialog_id=dialog_id,
            agent_name=f"BackgroundTask:{task_id}",
            event_bus=event_bus,
            state_machine=state_machine
        )
        self._task_id: str = task_id
        self._command: str = command
        self._process: Optional[subprocess.Popen] = None
        self._output_buffer: list[str] = []
        self._task_status: str = "initialized"  # initialized, running, completed, failed
        self._exit_code: Optional[int] = None
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None

    @property
    def task_id(self) -> str:
        """任务 ID"""
        return self._task_id

    @property
    def command(self) -> str:
        """执行的命令"""
        return self._command

    @property
    def task_status(self) -> str:
        """任务状态"""
        return self._task_status

    @property
    def exit_code(self) -> Optional[int]:
        """退出码"""
        return self._exit_code

    def _do_initialize(self) -> None:
        """子类初始化逻辑"""
        self._setup_transitions()

    async def start_process(self) -> MonitoringEvent:
        """
        启动后台进程

        Returns:
            生成的事件
        """
        self._task_status = "running"
        self._started_at = datetime.utcnow()
        self._transition_state(AgentState.BACKGROUND_TASKS, trigger="task_started")

        # 启动子进程
        try:
            self._process = subprocess.Popen(
                self._command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )

            # 启动输出读取线程
            threading.Thread(
                target=self._read_output,
                args=(self._process.stdout, False),
                daemon=True
            ).start()
            threading.Thread(
                target=self._read_output,
                args=(self._process.stderr, True),
                daemon=True
            ).start()

            # 启动监控线程
            threading.Thread(
                target=self._monitor_process,
                daemon=True
            ).start()

        except Exception as e:
            logger.error(f"[BackgroundTaskBridge] Failed to start process: {e}")
            return self.mark_failed(str(e))

        # 发送 BG_TASK_STARTED 事件
        payload = BgTaskStartedPayload(
            task_id=self._task_id,
            command=self._command[:200],  # 截断长命令
            bridge_id=str(self._bridge_id)
        )
        return self._emit(
            EventType.BG_TASK_STARTED,
            payload=payload.model_dump(),
            priority=EventPriority.HIGH
        )

    def _read_output(self, pipe, is_stderr: bool = False) -> None:
        """读取进程输出"""
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    line = line.rstrip('\n')
                    self._output_buffer.append(line)
                    # 直接发送实时输出事件（同步方式）
                    try:
                        self.stream_output(line, is_stderr)
                    except Exception as e:
                        logger.error(f"[BackgroundTaskBridge] Error emitting output: {e}")
            pipe.close()
        except Exception as e:
            logger.error(f"[BackgroundTaskBridge] Error reading output: {e}")

    def _monitor_process(self) -> None:
        """监控进程状态"""
        try:
            if self._process:
                exit_code = self._process.wait()
                self._exit_code = exit_code
                if exit_code == 0:
                    self.mark_completed(exit_code)
                else:
                    self.mark_failed(f"Exit code: {exit_code}", exit_code)
        except Exception as e:
            logger.error(f"[BackgroundTaskBridge] Error monitoring process: {e}")
            self.mark_failed(str(e))

    def stream_output(self, output: str, is_stderr: bool = False) -> MonitoringEvent:
        """
        流式输出

        Args:
            output: 输出内容
            is_stderr: 是否来自 stderr

        Returns:
            生成的事件
        """
        self._output_buffer.append(output)
        payload = BgTaskProgressPayload(
            task_id=self._task_id,
            output=output[:1000],  # 截断长输出
            is_stderr=is_stderr,
            buffer_size=len(self._output_buffer),
            bridge_id=str(self._bridge_id)
        )
        return self._emit(
            EventType.BG_TASK_PROGRESS,
            payload=payload.model_dump(),
            priority=EventPriority.LOW
        )

    def mark_completed(self, exit_code: int = 0) -> MonitoringEvent:
        """
        标记任务完成

        Args:
            exit_code: 退出码

        Returns:
            生成的事件
        """
        self._task_status = "completed"
        self._exit_code = exit_code
        self._completed_at = datetime.utcnow()
        self._transition_state(AgentState.COMPLETED, trigger="task_completed")

        duration_ms = 0
        if self._started_at:
            duration_ms = int((self._completed_at - self._started_at).total_seconds() * 1000)

        payload = BgTaskCompletedWithBridgePayload(
            task_id=self._task_id,
            exit_code=exit_code,
            duration_ms=duration_ms,
            output_lines=len(self._output_buffer),
            bridge_id=str(self._bridge_id)
        )
        return self._emit(
            EventType.BG_TASK_COMPLETED,
            payload=payload.model_dump(),
            priority=EventPriority.HIGH
        )

    def mark_failed(self, error: str, exit_code: Optional[int] = None) -> MonitoringEvent:
        """
        标记任务失败

        Args:
            error: 错误信息
            exit_code: 可选的退出码

        Returns:
            生成的事件
        """
        self._task_status = "failed"
        self._exit_code = exit_code
        self._completed_at = datetime.utcnow()
        self._transition_state(AgentState.ERROR, trigger="task_failed")
        payload = BgTaskFailedWithExitCodePayload(
            task_id=self._task_id,
            error=error,
            exit_code=exit_code,
            bridge_id=str(self._bridge_id)
        )
        return self._emit(
            EventType.BG_TASK_FAILED,
            payload=payload.model_dump(),
            priority=EventPriority.CRITICAL
        )

    def get_output(self) -> str:
        """获取完整输出"""
        return "".join(self._output_buffer)


class CompositeMonitoringBridge(BaseMonitoringBridge):
    """
    组合监控桥接器

    管理子智能体和后台任务的生命周期，实现 Composite 模式。

    Attributes:
        _children: 子桥接器字典
        _active_subagent: 当前活动的子智能体 ID
    """

    def __init__(
        self,
        dialog_id: str,
        agent_name: str,
        event_bus: EventBus,
        state_machine: Optional[StateMachine] = None
    ):
        """
        初始化组合监控桥接器

        Args:
            dialog_id: 对话框 ID
            agent_name: Agent 名称
            event_bus: 事件总线
            state_machine: 可选的状态机
        """
        super().__init__(
            dialog_id=dialog_id,
            agent_name=agent_name,
            event_bus=event_bus,
            state_machine=state_machine
        )
        self._children: dict[UUID, BaseMonitoringBridge] = {}
        self._active_subagent: Optional[UUID] = None

    def create_subagent_bridge(
        self,
        subagent_name: str,
        subagent_type: str = "Explore"
    ) -> ChildMonitoringBridge:
        """
        创建子智能体桥接器

        Args:
            subagent_name: 子智能体名称
            subagent_type: 子智能体类型

        Returns:
            ChildMonitoringBridge 实例
        """
        child = ChildMonitoringBridge(
            dialog_id=self._dialog_id,
            subagent_name=subagent_name,
            subagent_type=subagent_type,
            event_bus=self._event_bus,
            parent_bridge_id=self._bridge_id,
            state_machine=None  # 子桥接器使用自己的状态机
        )

        self._children[child.get_bridge_id()] = child
        self._active_subagent = child.get_bridge_id()

        # 发送 SUBAGENT_SPAWNED 事件
        spawned_payload = SubagentSpawnedWithParentPayload(
            subagent_id=str(child.get_bridge_id()),
            subagent_name=subagent_name,
            subagent_type=subagent_type,
            parent_bridge_id=str(self._bridge_id),
            parent_agent_name=self._agent_name
        )
        self._emit(
            EventType.SUBAGENT_SPAWNED,
            payload=spawned_payload.model_dump(),
            priority=EventPriority.HIGH
        )

        return child

    def create_background_task_bridge(
        self,
        task_id: str,
        command: str
    ) -> BackgroundTaskBridge:
        """
        创建后台任务桥接器

        Args:
            task_id: 任务 ID
            command: 执行的命令

        Returns:
            BackgroundTaskBridge 实例
        """
        task = BackgroundTaskBridge(
            dialog_id=self._dialog_id,
            task_id=task_id,
            command=command,
            event_bus=self._event_bus
        )

        self._children[task.get_bridge_id()] = task

        # 发送 BG_TASK_QUEUED 事件
        queued_payload = BgTaskQueuedPayload(
            task_id=task_id,
            command=command[:200],
            bridge_id=str(task.get_bridge_id()),
            parent_bridge_id=str(self._bridge_id)
        )
        self._emit(
            EventType.BG_TASK_QUEUED,
            payload=queued_payload.model_dump(),
            priority=EventPriority.NORMAL
        )

        return task

    def get_child(self, bridge_id: UUID) -> Optional[BaseMonitoringBridge]:
        """
        获取子桥接器

        Args:
            bridge_id: 桥接器 ID

        Returns:
            子桥接器实例或 None
        """
        return self._children.get(bridge_id)

    def get_all_bridges(self) -> dict[UUID, BaseMonitoringBridge]:
        """
        获取所有桥接器（包括自己）

        Returns:
            桥接器字典
        """
        result = {self._bridge_id: self}
        result.update(self._children)
        return result

    def get_subagent_bridges(self) -> list[ChildMonitoringBridge]:
        """获取所有子智能体桥接器"""
        return [
            bridge for bridge in self._children.values()
            if isinstance(bridge, ChildMonitoringBridge)
        ]

    def get_background_task_bridges(self) -> list[BackgroundTaskBridge]:
        """获取所有后台任务桥接器"""
        return [
            bridge for bridge in self._children.values()
            if isinstance(bridge, BackgroundTaskBridge)
        ]

    def set_active_subagent(self, bridge_id: Optional[UUID]) -> None:
        """
        设置当前活动的子智能体

        Args:
            bridge_id: 子智能体桥接器 ID，None 表示清除
        """
        if bridge_id is None or bridge_id in self._children:
            self._active_subagent = bridge_id

    def get_active_subagent_bridge(self) -> Optional[ChildMonitoringBridge]:
        """获取当前活动的子智能体桥接器"""
        if self._active_subagent:
            bridge = self._children.get(self._active_subagent)
            if isinstance(bridge, ChildMonitoringBridge):
                return bridge
        return None

    def remove_child(self, bridge_id: UUID) -> bool:
        """
        移除子桥接器

        Args:
            bridge_id: 桥接器 ID

        Returns:
            True 如果成功移除
        """
        if bridge_id in self._children:
            del self._children[bridge_id]
            if self._active_subagent == bridge_id:
                self._active_subagent = None
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "total_children": len(self._children),
            "subagent_count": len(self.get_subagent_bridges()),
            "background_task_count": len(self.get_background_task_bridges()),
            "active_subagent": str(self._active_subagent) if self._active_subagent else None,
            "parent_bridge_id": str(self._bridge_id),
            "parent_agent_name": self._agent_name
        }
