"""异步队列模块。

提供泛型异步队列抽象和内存实现。

Classes:
    AsyncQueue: 泛型异步队列抽象基类。
    InMemoryAsyncQueue: 基于内存的异步队列实现。

Exceptions:
    QueueFull: 队列已满异常。

Example:
    >>> from backend.infrastructure.queue import InMemoryAsyncQueue
    >>>
    >>> queue: InMemoryAsyncQueue[str] = InMemoryAsyncQueue(maxsize=100)
    >>> await queue.enqueue("hello")
    >>> async for item in queue.consume():
    ...     print(item)
"""

from .base import AsyncQueue, QueueFull
from .memory import InMemoryAsyncQueue

__all__ = ["AsyncQueue", "InMemoryAsyncQueue", "QueueFull"]
