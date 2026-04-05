"""异步队列的内存实现模块。

基于 asyncio.Queue 实现 AsyncQueue 抽象接口，提供单进程内存级队列功能。
"""

import asyncio
from typing import AsyncIterator, Generic, TypeVar

from .base import AsyncQueue, QueueFull

T = TypeVar("T")


class InMemoryAsyncQueue(AsyncQueue[T], Generic[T]):
    """基于内存的泛型异步队列实现。

    使用 asyncio.Queue 作为底层存储，提供完整的 AsyncQueue 接口实现。
    适用于单进程内的异步任务队列、消息缓冲等场景。

    Type Parameters:
        T: 队列元素类型。

    Args:
        maxsize: 队列最大容量。0 表示无限制（默认）。

    Example:
        >>> queue: InMemoryAsyncQueue[str] = InMemoryAsyncQueue(maxsize=100)
        >>> await queue.enqueue("hello")
        >>> async for item in queue.consume():
        ...     print(item)
    """

    def __init__(self, maxsize: int = 0) -> None:
        """初始化内存队列。

        Args:
            maxsize: 队列最大容量。0 表示无限制（默认）。
        """
        self._queue: asyncio.Queue[T] = asyncio.Queue(maxsize=maxsize)

    async def enqueue(
        self, item: T, block: bool = True, timeout: float | None = None
    ) -> None:
        """将元素异步加入队列。

        Args:
            item: 要入队的元素。
            block: 是否阻塞等待。为 True 时，若队列满则等待；
                   为 False 时，若队列满立即抛出 QueueFull 异常。
            timeout: 阻塞模式下的最大等待秒数。None 表示无限等待。

        Raises:
            QueueFull: 当 block=False 且队列已满时。
            TimeoutError: 当 block=True 且等待超时时。
        """
        if block:
            await asyncio.wait_for(self._queue.put(item), timeout=timeout)
        else:
            try:
                self._queue.put_nowait(item)
            except asyncio.QueueFull:
                raise QueueFull("Queue is full")

    def consume(self) -> AsyncIterator[T]:
        """返回异步迭代器用于消费队列元素。

        Returns:
            AsyncIterator[T]: 队列元素的异步迭代器。

        Note:
            每次调用都返回新的独立迭代器。
            元素只会被其中一个消费者获取（竞争消费模式）。
        """
        async def _generator() -> AsyncIterator[T]:
            while True:
                item = await self._queue.get()
                yield item
        return _generator()

    def full(self) -> bool:
        """检查队列是否已满。

        Returns:
            bool: 当队列达到最大容量时返回 True，否则返回 False。
        """
        return self._queue.full()

    def empty(self) -> bool:
        """检查队列是否为空。

        Returns:
            bool: 当队列中没有元素时返回 True，否则返回 False。
        """
        return self._queue.empty()

    def qsize(self) -> int:
        """返回队列中的元素数量。

        Returns:
            int: 当前队列中的元素个数。
        """
        return self._queue.qsize()
