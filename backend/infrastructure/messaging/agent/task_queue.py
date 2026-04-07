"""AgentTaskQueue - Agent 任务队列管理器

管理 Agent 任务的提交和执行，提供并发控制和优先级支持。

Example:
    >>> from backend.infrastructure.messaging.agent import AgentTaskQueue, AgentTask
    >>> from backend.infrastructure.messaging.agent.task_queue import TaskPriority
    >>>
    >>> # 创建任务队列（最多3个并发）
    >>> queue = AgentTaskQueue(max_concurrent=3)
    >>> await queue.start()
    >>>
    >>> # 提交任务
    >>> task = AgentTask(
    ...     task_id="task_001",
    ...     dialog_id="dlg_001",
    ...     action="send_message",
    ...     priority=TaskPriority.HIGH
    ... )
    >>> future = await queue.submit(task)
    >>>
    >>> # 等待任务完成
    >>> result = await future
    >>>
    >>> await queue.shutdown()
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from backend.logging import get_logger
from backend.infrastructure.messaging.core import InMemoryAsyncQueue

logger = get_logger(__name__)


class TaskPriority(Enum):
    """任务优先级"""

    CRITICAL = 0  # 关键任务，最高优先级
    HIGH = 1  # 高优先级
    NORMAL = 2  # 普通优先级
    LOW = 3  # 低优先级
    BACKGROUND = 4  # 后台任务，最低优先级


@dataclass
class AgentTask:
    """Agent 任务数据类

    Attributes:
        task_id: 任务唯一标识
        dialog_id: 关联的对话 ID
        action: 任务动作类型
        payload: 任务负载数据
        priority: 任务优先级
        created_at: 创建时间
    """

    task_id: str
    dialog_id: str
    action: str
    payload: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskResult:
    """任务执行结果

    Attributes:
        task_id: 任务 ID
        success: 是否成功
        result: 执行结果（成功时）
        error: 错误信息（失败时）
    """

    task_id: str
    success: bool
    result: Any = None
    error: str | None = None


class AgentTaskQueue:
    """Agent 任务队列管理器

    提供：
    - 任务提交和排队
    - 并发控制（通过信号量）
    - 优先级支持（高优先级优先执行）
    - 执行结果返回（Future 模式）

    Attributes:
        max_concurrent: 最大并发执行数
        _task_queue: 任务队列（带优先级）
        _semaphore: 并发控制信号量
        _running: 是否正在运行

    Example:
        >>> queue = AgentTaskQueue(max_concurrent=5)
        >>> await queue.start()
        >>>
        >>> # 提交任务并获取 Future
        >>> future = await queue.submit(task)
        >>> result = await future
        >>>
        >>> await queue.shutdown()
    """

    def __init__(self, max_concurrent: int = 5):
        """初始化 AgentTaskQueue

        Args:
            max_concurrent: 最大并发执行数（默认 5）
        """
        self.max_concurrent = max_concurrent
        self._task_queue: InMemoryAsyncQueue[tuple[int, AgentTask, asyncio.Future]] = (
            InMemoryAsyncQueue()
        )
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False
        self._worker_task: asyncio.Task | None = None
        self._stats = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
        }

    async def start(self) -> None:
        """启动任务队列，启动工作线程"""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info(f"[AgentTaskQueue] Started with max_concurrent={self.max_concurrent}")

    async def shutdown(self) -> None:
        """优雅关闭任务队列"""
        if not self._running:
            return

        self._running = False
        logger.info("[AgentTaskQueue] Shutting down...")

        # 等待队列排空（最多 10 秒）
        for _ in range(100):
            if self._task_queue.empty():
                break
            await asyncio.sleep(0.1)

        # 取消工作线程
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("[AgentTaskQueue] Shutdown complete")

    async def submit(self, task: AgentTask) -> asyncio.Future:
        """提交任务到队列

        Args:
            task: AgentTask 实例

        Returns:
            Future，可用于获取任务执行结果

        Raises:
            RuntimeError: 如果队列未启动
        """
        if not self._running:
            raise RuntimeError("TaskQueue not started. Call start() first.")

        future = asyncio.get_event_loop().create_future()
        # 优先级值越小优先级越高
        await self._task_queue.enqueue((task.priority.value, task, future))
        self._stats["submitted"] += 1

        logger.debug(
            f"[AgentTaskQueue] Task {task.task_id} submitted with priority {task.priority.name}"
        )
        return future

    async def _worker_loop(self) -> None:
        """工作线程循环，消费并执行任务"""
        while self._running:
            try:
                # 从队列获取任务（已按优先级排序）
                async for priority, task, future in self._task_queue.consume():
                    # 使用信号量控制并发
                    async with self._semaphore:
                        result = await self._execute_task(task)

                    # 设置 Future 结果
                    if not future.done():
                        if result.success:
                            future.set_result(result.result)
                        else:
                            future.set_exception(RuntimeError(result.error or "Unknown error"))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"[AgentTaskQueue] Worker error: {e}")

    async def _execute_task(self, task: AgentTask) -> TaskResult:
        """执行单个任务

        Args:
            task: 要执行的任务

        Returns:
            TaskResult 执行结果
        """
        logger.info(f"[AgentTaskQueue] Executing task {task.task_id}: {task.action}")

        try:
            # 模拟任务执行
            # 实际项目中这里会调用具体的 Agent 逻辑
            await asyncio.sleep(0.1)  # 模拟执行时间

            result = TaskResult(
                task_id=task.task_id,
                success=True,
                result={"status": "completed", "task_id": task.task_id},
            )
            self._stats["completed"] += 1
            logger.info(f"[AgentTaskQueue] Task {task.task_id} completed")

        except Exception as e:
            result = TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
            )
            self._stats["failed"] += 1
            logger.error(f"[AgentTaskQueue] Task {task.task_id} failed: {e}")

        return result

    def get_stats(self) -> dict:
        """获取队列统计信息

        Returns:
            包含提交数、完成数、失败数、等待数的字典
        """
        return {
            "running": self._running,
            "max_concurrent": self.max_concurrent,
            "queue_size": self._task_queue.qsize(),
            "submitted": self._stats["submitted"],
            "completed": self._stats["completed"],
            "failed": self._stats["failed"],
            "pending": self._stats["submitted"] - self._stats["completed"] - self._stats["failed"],
        }
