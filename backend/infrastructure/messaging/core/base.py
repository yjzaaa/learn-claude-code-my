"""异步队列抽象基类模块。

提供泛型异步队列抽象接口，支持类型安全的入队和消费操作。

Usage Example:
    >>> from backend.infrastructure.messaging.core import InMemoryAsyncQueue
    >>>
    >>> queue: InMemoryAsyncQueue[str] = InMemoryAsyncQueue(maxsize=100)
    >>> await queue.enqueue("hello")
    >>> async for item in queue.consume():
    ...     print(item)
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Generic, TypeVar

T = TypeVar("T")


class QueueFull(Exception):
    """当队列已满且非阻塞入队时抛出。"""

    pass


class AsyncQueue(ABC, Generic[T]):
    """泛型异步队列抽象基类。

    提供类型安全的异步队列接口，支持通过泛型参数 T 指定队列元素类型。

    Type Parameters:
        T: 队列元素类型。静态类型检查器会验证入队/消费操作的类型一致性。

    Example:
        >>> class MyEvent:
        ...     pass
        >>>
        >>> queue: AsyncQueue[MyEvent] = InMemoryAsyncQueue()
        >>> await queue.enqueue(MyEvent())  # 类型检查通过
        >>> # await queue.enqueue("string")  # 类型检查错误
    """

    @abstractmethod
    async def enqueue(self, item: T, block: bool = True, timeout: float | None = None) -> None:
        """将元素异步加入队列。

        Args:
            item: 要入队的元素，类型必须与泛型参数 T 一致。
            block: 是否阻塞等待。为 True 时，若队列满则等待；
                   为 False 时，若队列满立即抛出 QueueFull 异常。
            timeout: 阻塞模式下的最大等待秒数。None 表示无限等待。

        Raises:
            QueueFull: 当 block=False 且队列已满时。
            TimeoutError: 当 block=True 且等待超时时。

        Example:
            >>> await queue.enqueue(item)
            >>> await queue.enqueue(item, timeout=5.0)
            >>> await queue.enqueue(item, block=False)
        """
        ...

    @abstractmethod
    def consume(self) -> AsyncIterator[T]:
        """返回异步迭代器用于消费队列元素。

        迭代器按 FIFO 顺序返回元素。当队列为空时，异步等待新元素入队。

        Returns:
            AsyncIterator[T]: 队列元素的异步迭代器。

        Example:
            >>> async for item in queue.consume():
            ...     await process(item)

        Note:
            多个消费者可以同时调用此方法，各自获得独立的迭代器。
            元素只会被其中一个消费者获取（竞争消费）。
        """
        ...

    @abstractmethod
    def full(self) -> bool:
        """检查队列是否已满。

        Returns:
            bool: 当队列达到最大容量时返回 True，否则返回 False。
        """
        ...

    @abstractmethod
    def empty(self) -> bool:
        """检查队列是否为空。

        Returns:
            bool: 当队列中没有元素时返回 True，否则返回 False。
        """
        ...

    @abstractmethod
    def qsize(self) -> int:
        """返回队列中的元素数量。

        Returns:
            int: 当前队列中的元素个数。
        """
        ...
