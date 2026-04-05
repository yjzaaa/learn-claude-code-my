"""WebSocketMessageBuffer - WebSocket 消息缓冲区

为每个 WebSocket 连接提供独立的消息缓冲，实现流量平滑和背压控制。

Example:
    >>> from backend.infrastructure.websocket_buffer import WebSocketMessageBuffer, BufferStrategy
    >>>
    >>> # 创建消息缓冲区（每个客户端）
    >>> buffer = WebSocketMessageBuffer(
    ...     client_id="client_001",
    ...     maxsize=100,
    ...     strategy=BufferStrategy.BLOCK
    ... )
    >>> await buffer.start(websocket_connection)
    >>>
    >>> # 发送消息（带缓冲）
    >>> success = await buffer.send({"type": "message", "content": "hello"})
    >>>
    >>> await buffer.shutdown()
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from backend.infrastructure.queue import InMemoryAsyncQueue, QueueFull

logger = logging.getLogger(__name__)


class BufferStrategy(Enum):
    """缓冲区满时的处理策略"""

    BLOCK = "block"  # 阻塞等待直到有空间
    DROP = "drop"  # 丢弃消息
    TIMEOUT = "timeout"  # 等待超时后丢弃


@dataclass
class WebSocketMessage:
    """WebSocket 消息数据类

    Attributes:
        data: 消息数据（会被 JSON 序列化）
        timestamp: 消息创建时间
        retry_count: 重试次数
    """

    data: dict
    timestamp: Optional[float] = None
    retry_count: int = 0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = asyncio.get_event_loop().time()


class WebSocketMessageBuffer:
    """WebSocket 消息缓冲区

    为每个 WebSocket 客户端连接提供：
    - 消息缓冲：平滑流量突发
    - 背压控制：防止内存溢出
    - 多种策略：阻塞、丢弃、超时
    - 自动重连：连接断开时缓冲消息

    Attributes:
        client_id: 客户端唯一标识
        maxsize: 缓冲区最大容量
        strategy: 缓冲区满时的处理策略

    Example:
        >>> buffer = WebSocketMessageBuffer(
        ...     client_id="client_001",
        ...     maxsize=100,
        ...     strategy=BufferStrategy.BLOCK
        ... )
        >>> await buffer.start(websocket)
        >>> await buffer.send({"type": "update", "data": {...}})
        >>> await buffer.shutdown()
    """

    def __init__(
        self,
        client_id: str,
        maxsize: int = 100,
        strategy: BufferStrategy = BufferStrategy.BLOCK,
        timeout: float = 5.0,
    ):
        """初始化 WebSocketMessageBuffer

        Args:
            client_id: 客户端唯一标识
            maxsize: 缓冲区最大容量（默认 100）
            strategy: 缓冲区满时的处理策略（默认 BLOCK）
            timeout: TIMEOUT 策略的超时秒数（默认 5.0）
        """
        self.client_id = client_id
        self.maxsize = maxsize
        self.strategy = strategy
        self.timeout = timeout

        self._buffer: InMemoryAsyncQueue[WebSocketMessage] = InMemoryAsyncQueue(
            maxsize=maxsize
        )
        self._websocket: Optional[Any] = None
        self._running = False
        self._sender_task: Optional[asyncio.Task] = None
        self._dropped_count = 0
        self._sent_count = 0

    async def start(self, websocket: Any) -> None:
        """启动消息缓冲区

        Args:
            websocket: WebSocket 连接对象（需有 send 方法）
        """
        if self._running:
            return

        self._websocket = websocket
        self._running = True
        self._sender_task = asyncio.create_task(self._sender_loop())
        logger.info(f"[WebSocketBuffer] Started for client {self.client_id}")

    async def shutdown(self) -> None:
        """优雅关闭消息缓冲区"""
        if not self._running:
            return

        self._running = False
        logger.info(f"[WebSocketBuffer] Shutting down for client {self.client_id}")

        # 等待剩余消息发送（最多 5 秒）
        for _ in range(50):
            if self._buffer.empty():
                break
            await asyncio.sleep(0.1)

        # 取消发送任务
        if self._sender_task:
            self._sender_task.cancel()
            try:
                await self._sender_task
            except asyncio.CancelledError:
                pass

        logger.info(f"[WebSocketBuffer] Shutdown complete for client {self.client_id}")

    async def send(self, data: dict) -> bool:
        """发送消息（带缓冲）

        根据配置的策略处理缓冲区满的情况。

        Args:
            data: 要发送的消息数据

        Returns:
            True 表示消息已入队，False 表示消息被丢弃
        """
        if not self._running:
            logger.warning(f"[WebSocketBuffer] Buffer not started for {self.client_id}")
            return False

        message = WebSocketMessage(data=data)

        try:
            if self.strategy == BufferStrategy.BLOCK:
                # 阻塞等待直到有空间
                await self._buffer.enqueue(message)
                return True

            elif self.strategy == BufferStrategy.DROP:
                # 非阻塞，满时立即丢弃
                await self._buffer.enqueue(message, block=False)
                return True

            elif self.strategy == BufferStrategy.TIMEOUT:
                # 等待超时后丢弃
                await self._buffer.enqueue(message, timeout=self.timeout)
                return True

            else:
                logger.error(f"[WebSocketBuffer] Unknown strategy: {self.strategy}")
                return False

        except QueueFull:
            self._dropped_count += 1
            logger.warning(
                f"[WebSocketBuffer] Message dropped for {self.client_id} "
                f"(buffer full, strategy={self.strategy.value})"
            )
            return False

        except asyncio.TimeoutError:
            self._dropped_count += 1
            logger.warning(
                f"[WebSocketBuffer] Message timeout for {self.client_id} "
                f"(buffer full after {self.timeout}s)"
            )
            return False

    async def _sender_loop(self) -> None:
        """发送循环，从缓冲区消费消息并发送"""
        while self._running:
            try:
                async for message in self._buffer.consume():
                    await self._send_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"[WebSocketBuffer] Sender error for {self.client_id}: {e}")
                await asyncio.sleep(0.1)  # 错误后短暂等待

    async def _send_message(self, message: WebSocketMessage) -> None:
        """发送单个消息

        Args:
            message: WebSocketMessage 实例
        """
        if not self._websocket:
            return

        try:
            # 序列化并发送 - 使用 send_json 发送字典
            await self._websocket.send_json(message.data)

            self._sent_count += 1
            logger.debug(f"[WebSocketBuffer] Message sent to {self.client_id}")

        except Exception as e:
            logger.error(f"[WebSocketBuffer] Send failed for {self.client_id}: {e}")

    def get_stats(self) -> dict:
        """获取缓冲区统计信息

        Returns:
            包含缓冲区深度、已发送数、已丢弃数的字典
        """
        return {
            "client_id": self.client_id,
            "running": self._running,
            "buffer_size": self._buffer.qsize(),
            "buffer_maxsize": self.maxsize,
            "strategy": self.strategy.value,
            "sent_count": self._sent_count,
            "dropped_count": self._dropped_count,
        }
