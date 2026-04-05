"""Logging Mixin - 日志混入类 (AsyncQueue 改造版)

使用 AsyncQueue 实现异步日志缓冲，减少 I/O 阻塞。
集中管理所有 jsonl 文件写入操作。
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from backend.infrastructure.queue import InMemoryAsyncQueue


@dataclass
class LogEntry:
    """日志条目"""
    level: str
    message: str
    dialog_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    extra: dict[str, Any] = field(default_factory=dict)


class AsyncLogBuffer:
    """异步日志缓冲区

    使用 AsyncQueue 缓冲日志消息，批量处理减少 I/O。

    Attributes:
        maxsize: 缓冲区最大容量
        flush_interval: 自动刷新间隔（秒）
        batch_size: 批量处理大小
    """

    def __init__(
        self,
        name: str,
        maxsize: int = 1000,
        flush_interval: float = 1.0,
        batch_size: int = 10
    ):
        self.name = name
        self.maxsize = maxsize
        self.flush_interval = flush_interval
        self.batch_size = batch_size

        self._queue: InMemoryAsyncQueue[LogEntry] = InMemoryAsyncQueue(maxsize=maxsize)
        self._logger = logger.bind(name=name)
        self._running = False
        self._flush_task: Optional[asyncio.Task[Any]] = None
        self._stats = {
            "buffered": 0,
            "flushed": 0,
            "dropped": 0,
        }

    async def start(self) -> None:
        """启动日志缓冲区"""
        if self._running:
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.debug(f"[AsyncLogBuffer:{self.name}] Started")

    async def stop(self) -> None:
        """停止日志缓冲区，排空队列"""
        if not self._running:
            return

        self._running = False

        # 最后一次刷新
        await self._flush_all()

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        logger.debug(f"[AsyncLogBuffer:{self.name}] Stopped")

    async def log(
        self,
        level: str,
        message: str,
        dialog_id: Optional[str] = None,
        **extra
    ) -> bool:
        """异步记录日志

        Args:
            level: 日志级别 (debug, info, warning, error)
            message: 日志消息
            dialog_id: 对话 ID
            **extra: 额外字段

        Returns:
            True 表示成功缓冲，False 表示队列满
        """
        entry = LogEntry(
            level=level,
            message=message,
            dialog_id=dialog_id,
            extra=extra
        )

        try:
            await self._queue.enqueue(entry, block=False)
            self._stats["buffered"] += 1
            return True
        except Exception:
            self._stats["dropped"] += 1
            return False

    async def _flush_loop(self) -> None:
        """刷新循环，定期批量处理日志"""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[AsyncLogBuffer:{self.name}] Flush error: {e}")

    async def _flush_batch(self) -> None:
        """批量刷新日志"""
        batch: list[LogEntry] = []

        # 收集一批日志（最多 batch_size 个或直到队列为空）
        for _ in range(self.batch_size):
            if self._queue.empty():
                break
            try:
                # 使用 consume 迭代器获取一个元素
                # 由于 consume 返回 AsyncIterator，我们使用 asyncio.wait_for 来避免阻塞
                iterator = self._queue.consume()
                entry = await asyncio.wait_for(iterator.__anext__(), timeout=0.1)
                batch.append(entry)
            except asyncio.TimeoutError:
                # 超时，没有更多元素
                break
            except StopAsyncIteration:
                # 迭代器结束
                break
            except Exception:
                break

        if not batch:
            return

        # 批量写入
        for entry in batch:
            self._write_entry(entry)

        self._stats["flushed"] += len(batch)

    async def _flush_all(self) -> None:
        """刷新所有剩余日志"""
        while not self._queue.empty():
            await self._flush_batch()

    def _write_entry(self, entry: LogEntry) -> None:
        """写入单条日志"""
        log_func = getattr(self._logger, entry.level, self._logger.info)

        extra_info = ""
        if entry.dialog_id:
            extra_info += f" dialog_id={entry.dialog_id}"
        if entry.extra:
            extra_info += f" extra={entry.extra}"

        log_func(f"{entry.message}{extra_info}")

    def get_stats(self) -> dict[str, Any]:
        """获取缓冲区统计"""
        return {
            "name": self.name,
            "running": self._running,
            "queue_size": self._queue.qsize(),
            "buffered": self._stats["buffered"],
            "flushed": self._stats["flushed"],
            "dropped": self._stats["dropped"],
        }


class DeepLoggingMixin:
    """Deep Runtime 日志混入类 (AsyncQueue 改造版)

    提供 Deep Agent Runtime 的异步日志记录功能。
    使用 AsyncQueue 缓冲日志，减少 I/O 阻塞。

    Example:
        >>> class MyRuntime(DeepLoggingMixin):
        ...     async def start(self):
        ...         await self._init_async_loggers()
        ...     async def stop(self):
        ...         await self._stop_async_loggers()
        ...     async def process(self):
        ...         await self._alog_message_chunk(chunk, "dlg_001", "content")
    """

    def __init__(self):
        self._msg_log_buffer: Optional[AsyncLogBuffer] = None
        self._update_log_buffer: Optional[AsyncLogBuffer] = None
        self._value_log_buffer: Optional[AsyncLogBuffer] = None

    async def _init_async_loggers(self) -> None:
        """初始化异步日志记录器"""
        # 创建异步日志缓冲区
        self._msg_log_buffer = AsyncLogBuffer(
            name="deep_messages",
            maxsize=1000,
            flush_interval=0.5,  # 500ms 刷新一次
            batch_size=10
        )
        self._update_log_buffer = AsyncLogBuffer(
            name="deep_updates",
            maxsize=500,
            flush_interval=1.0,
            batch_size=5
        )
        self._value_log_buffer = AsyncLogBuffer(
            name="deep_values",
            maxsize=500,
            flush_interval=1.0,
            batch_size=5
        )

        # 启动所有缓冲区
        await self._msg_log_buffer.start()
        await self._update_log_buffer.start()
        await self._value_log_buffer.start()

        logger.debug("[DeepLoggingMixin] Async loggers initialized")

    async def _stop_async_loggers(self) -> None:
        """停止异步日志记录器"""
        if self._msg_log_buffer:
            await self._msg_log_buffer.stop()
        if self._update_log_buffer:
            await self._update_log_buffer.stop()
        if self._value_log_buffer:
            await self._value_log_buffer.stop()

        logger.debug("[DeepLoggingMixin] Async loggers stopped")

    async def _alog_message_chunk(
        self,
        message_chunk: Any,
        dialog_id: str,
        accumulated: str
    ) -> bool:
        """异步记录消息块

        Args:
            message_chunk: 消息块对象
            dialog_id: 对话 ID
            accumulated: 累积内容

        Returns:
            True 表示成功缓冲
        """
        if not self._msg_log_buffer:
            return False

        content = str(getattr(message_chunk, 'content', ''))[:100]
        message = f"Message chunk: content={content}, accumulated_len={len(accumulated)}"

        return await self._msg_log_buffer.log(
            level="debug",
            message=message,
            dialog_id=dialog_id
        )

    async def _alog_update(self, update_type: str, data: dict[str, Any], dialog_id: str) -> bool:
        """异步记录更新

        Args:
            update_type: 更新类型
            data: 更新数据
            dialog_id: 对话 ID

        Returns:
            True 表示成功缓冲
        """
        if not self._update_log_buffer:
            return False

        return await self._update_log_buffer.log(
            level="info",
            message=f"Update: type={update_type}",
            dialog_id=dialog_id,
            data=data
        )

    async def _alog_value(self, key: str, value: Any, dialog_id: str) -> bool:
        """异步记录值

        Args:
            key: 值键名
            value: 值
            dialog_id: 对话 ID

        Returns:
            True 表示成功缓冲
        """
        if not self._value_log_buffer:
            return False

        return await self._value_log_buffer.log(
            level="debug",
            message=f"Value: {key}={str(value)[:50]}",
            dialog_id=dialog_id,
            key=key
        )

    def get_log_stats(self) -> dict[str, Any]:
        """获取日志统计信息"""
        return {
            "messages": self._msg_log_buffer.get_stats() if self._msg_log_buffer else None,
            "updates": self._update_log_buffer.get_stats() if self._update_log_buffer else None,
            "values": self._value_log_buffer.get_stats() if self._value_log_buffer else None,
        }


class JsonlLogBuffer:
    """JSON Lines 日志缓冲区

    专门用于异步写入 jsonl 文件，支持：
    - 异步缓冲写入
    - 批量刷新
    - 自动文件轮转
    - 多文件类型管理

    Example:
        >>> buffer = JsonlLogBuffer(log_dir="logs/deep")
        >>> await buffer.start()
        >>> await buffer.write("raw_event", {"event": "test"})
        >>> await buffer.write("tool_results", {"tool": "sql", "result": "..."})
        >>> await buffer.stop()
    """

    def __init__(
        self,
        log_dir: str = "logs/deep",
        maxsize: int = 1000,
        flush_interval: float = 2.0,
        batch_size: int = 50
    ):
        self.log_dir = Path(log_dir)
        self.maxsize = maxsize
        self.flush_interval = flush_interval
        self.batch_size = batch_size

        self._queues: dict[str, InMemoryAsyncQueue[dict[str, Any]]] = {}
        self._running = False
        self._flush_task: Optional[asyncio.Task[Any]] = None
        self._stats: dict[str, dict[str, Any]] = {}

    async def start(self) -> None:
        """启动 JSONL 日志缓冲区"""
        if self._running:
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())

        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"[JsonlLogBuffer] Started, log_dir={self.log_dir}")

    async def stop(self) -> None:
        """停止并排空所有队列"""
        if not self._running:
            return

        self._running = False

        # 最后一次刷新
        await self._flush_all()

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        logger.debug(f"[JsonlLogBuffer] Stopped")

    async def write(self, log_type: str, data: dict[str, Any]) -> bool:
        """异步写入 JSONL 日志

        Args:
            log_type: 日志类型（如 raw_event, tool_results）
            data: 要写入的 JSON 数据

        Returns:
            True 表示成功缓冲
        """
        # 延迟创建队列
        if log_type not in self._queues:
            self._queues[log_type] = InMemoryAsyncQueue(maxsize=self.maxsize)
            self._stats[log_type] = {"buffered": 0, "flushed": 0, "dropped": 0}

        queue = self._queues[log_type]
        stats = self._stats[log_type]

        try:
            await queue.enqueue(data, block=False)
            stats["buffered"] += 1
            return True
        except Exception:
            stats["dropped"] += 1
            return False

    async def _flush_loop(self) -> None:
        """定期刷新循环"""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[JsonlLogBuffer] Flush error: {e}")

    async def _flush_all(self) -> None:
        """刷新所有队列"""
        for log_type, queue in self._queues.items():
            await self._flush_queue(log_type, queue)

    async def _flush_queue(self, log_type: str, queue: InMemoryAsyncQueue[dict[str, Any]]) -> None:
        """刷新单个队列到文件"""
        if queue.empty():
            return

        log_file = self.log_dir / f"{log_type}.jsonl"
        batch: list[dict[str, Any]] = []

        # 收集一批数据（最多 batch_size 个）
        # 使用 get_nowait 避免阻塞和复杂的迭代器管理
        for _ in range(self.batch_size):
            if queue.empty():
                break
            try:
                # 使用队列内部的 _queue.get_nowait() 方法
                entry = queue._queue.get_nowait()
                batch.append(entry)
            except Exception:
                break

        if not batch:
            return

        # 写入文件
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                for entry in batch:
                    json_str = json.dumps(entry, ensure_ascii=False, default=str)
                    f.write(json_str + "\n")

            self._stats[log_type]["flushed"] += len(batch)
            logger.debug(f"[JsonlLogBuffer] Flushed {len(batch)} entries to {log_type}.jsonl")
        except Exception as e:
            logger.error(f"[JsonlLogBuffer] Write error for {log_type}: {e}")

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "log_dir": str(self.log_dir),
            "running": self._running,
            "log_types": list(self._queues.keys()),
            "stats": self._stats.copy(),
        }


class UnifiedLoggingMixin:
    """统一日志混入类

    整合所有日志功能：
    - 异步日志缓冲 (AsyncLogBuffer)
    - JSONL 文件日志 (JsonlLogBuffer)
    - 提供统一的日志接口

    Example:
        >>> class MyRuntime(UnifiedLoggingMixin):
        ...     async def start(self):
        ...         await self._init_unified_loggers()
        ...     async def process(self):
        ...         await self._log_event("raw_event", {...})
        ...         await self._log_tool_result("sql", {...})
    """

    def __init__(self):
        # 普通日志缓冲区
        self._msg_log_buffer: Optional[AsyncLogBuffer] = None
        self._update_log_buffer: Optional[AsyncLogBuffer] = None
        self._value_log_buffer: Optional[AsyncLogBuffer] = None

        # JSONL 文件日志缓冲区
        self._jsonl_buffer: Optional[JsonlLogBuffer] = None

        # 同步日志记录器 (兼容旧代码)
        self._msg_logger = logger.bind(name="deep_messages")
        self._update_logger = logger.bind(name="deep_updates")
        self._value_logger = logger.bind(name="deep_values")

    async def _init_unified_loggers(self, log_dir: str = "logs/deep") -> None:
        """初始化统一日志记录器"""
        # 初始化普通日志缓冲区
        self._msg_log_buffer = AsyncLogBuffer(
            name="deep_messages",
            maxsize=1000,
            flush_interval=0.5,
            batch_size=10
        )
        self._update_log_buffer = AsyncLogBuffer(
            name="deep_updates",
            maxsize=500,
            flush_interval=1.0,
            batch_size=5
        )
        self._value_log_buffer = AsyncLogBuffer(
            name="deep_values",
            maxsize=500,
            flush_interval=1.0,
            batch_size=5
        )

        # 初始化 JSONL 缓冲区
        self._jsonl_buffer = JsonlLogBuffer(
            log_dir=log_dir,
            maxsize=2000,
            flush_interval=2.0,
            batch_size=100
        )

        # 启动所有缓冲区
        await self._msg_log_buffer.start()
        await self._update_log_buffer.start()
        await self._value_log_buffer.start()
        await self._jsonl_buffer.start()

        logger.debug("[UnifiedLoggingMixin] All loggers initialized")

    async def _stop_unified_loggers(self) -> None:
        """停止所有日志记录器"""
        if self._msg_log_buffer:
            await self._msg_log_buffer.stop()
        if self._update_log_buffer:
            await self._update_log_buffer.stop()
        if self._value_log_buffer:
            await self._value_log_buffer.stop()
        if self._jsonl_buffer:
            await self._jsonl_buffer.stop()

        logger.debug("[UnifiedLoggingMixin] All loggers stopped")

    # ═════════════════════════════════════════════════════════════════
    # 普通日志接口
    # ═════════════════════════════════════════════════════════════════

    async def _alog_message_chunk(
        self, message_chunk: Any, dialog_id: str, accumulated: str
    ) -> bool:
        """异步记录消息块"""
        if not self._msg_log_buffer:
            return False
        content = str(getattr(message_chunk, 'content', ''))[:100]
        return await self._msg_log_buffer.log(
            level="debug",
            message=f"Message chunk: content={content}, accumulated_len={len(accumulated)}",
            dialog_id=dialog_id
        )

    async def _alog_update(self, update_type: str, data: dict[str, Any], dialog_id: str) -> bool:
        """异步记录更新"""
        if not self._update_log_buffer:
            return False
        return await self._update_log_buffer.log(
            level="info",
            message=f"Update: type={update_type}",
            dialog_id=dialog_id,
            data=data
        )

    async def _alog_value(self, key: str, value: Any, dialog_id: str) -> bool:
        """异步记录值"""
        if not self._value_log_buffer:
            return False
        return await self._value_log_buffer.log(
            level="debug",
            message=f"Value: {key}={str(value)[:50]}",
            dialog_id=dialog_id,
            key=key
        )

    # ═════════════════════════════════════════════════════════════════
    # JSONL 日志接口（集中管理所有 jsonl 写入）
    # ═════════════════════════════════════════════════════════════════

    async def _log_event(self, event_type: str, data: dict[str, Any], dialog_id: Optional[str] = None) -> bool:
        """记录事件到 raw_event.jsonl

        替代 deep.py 中的直接文件写入
        """
        if not self._jsonl_buffer:
            return False

        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "dialog_id": dialog_id,
            **data
        }
        return await self._jsonl_buffer.write("raw_event", entry)

    async def _log_tool_result(
        self,
        tool_name: str,
        arguments: dict,
        result: Any,
        dialog_id: str,
        duration_ms: Optional[int] = None
    ) -> bool:
        """记录工具调用结果到 tool_results.jsonl

        替代 deep.py 和 simple.py 中的直接文件写入
        """
        if not self._jsonl_buffer:
            return False

        entry = {
            "timestamp": datetime.now().isoformat(),
            "dialog_id": dialog_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "result": str(result)[:1000] if result else None,  # 限制结果长度
            "duration_ms": duration_ms,
        }
        return await self._jsonl_buffer.write("tool_results", entry)

    async def _log_transcript(self, messages: list, metadata: dict) -> bool:
        """记录对话转录到 transcript.jsonl

        替代 compact_plugin.py 和 claude_compression.py 中的直接文件写入
        """
        if not self._jsonl_buffer:
            return False

        entry = {
            "timestamp": datetime.now().isoformat(),
            "messages": messages,
            **metadata
        }
        return await self._jsonl_buffer.write("transcript", entry)

    # ═════════════════════════════════════════════════════════════════
    # Fire-and-Forget 日志接口（同步调用，不阻塞主流程）
    # ═════════════════════════════════════════════════════════════════

    def _fire_log_msg(self, level: str, message: str, dialog_id: Optional[str] = None) -> None:
        """Fire-and-forget 记录消息日志（同步调用，不阻塞）"""
        if not self._msg_log_buffer:
            return
        import asyncio
        try:
            asyncio.create_task(self._msg_log_buffer.log(level, message, dialog_id))
        except Exception:
            pass

    def _fire_log_update(self, level: str, message: str, dialog_id: Optional[str] = None, **extra) -> None:
        """Fire-and-forget 记录更新日志（同步调用，不阻塞）"""
        if not self._update_log_buffer:
            return
        import asyncio
        try:
            asyncio.create_task(self._update_log_buffer.log(level, message, dialog_id, **extra))
        except Exception:
            pass

    def _fire_log_value(self, level: str, message: str, dialog_id: Optional[str] = None, **extra) -> None:
        """Fire-and-forget 记录值日志（同步调用，不阻塞）"""
        if not self._value_log_buffer:
            return
        import asyncio
        try:
            asyncio.create_task(self._value_log_buffer.log(level, message, dialog_id, **extra))
        except Exception:
            pass

    def _fire_log_event(self, event_type: str, data: dict, dialog_id: Optional[str] = None) -> None:
        """Fire-and-forget 记录事件到 raw_event.jsonl（同步调用，不阻塞）"""
        if not self._jsonl_buffer:
            return
        import asyncio
        from datetime import datetime
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "dialog_id": dialog_id,
            **data
        }
        try:
            asyncio.create_task(self._jsonl_buffer.write("raw_event", entry))
        except Exception:
            pass

    def _fire_log_tool_result(
        self,
        tool_name: str,
        arguments: dict,
        result: Any,
        dialog_id: str,
        duration_ms: Optional[int] = None
    ) -> None:
        """Fire-and-forget 记录工具调用结果到 tool_results.jsonl（同步调用，不阻塞）"""
        if not self._jsonl_buffer:
            return
        import asyncio
        from datetime import datetime
        entry = {
            "timestamp": datetime.now().isoformat(),
            "dialog_id": dialog_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "result": str(result)[:1000] if result else None,
            "duration_ms": duration_ms,
        }
        try:
            asyncio.create_task(self._jsonl_buffer.write("tool_results", entry))
        except Exception:
            pass

    def get_log_stats(self) -> dict[str, Any]:
        """获取所有日志统计"""
        return {
            "buffers": {
                "messages": self._msg_log_buffer.get_stats() if self._msg_log_buffer else None,
                "updates": self._update_log_buffer.get_stats() if self._update_log_buffer else None,
                "values": self._value_log_buffer.get_stats() if self._value_log_buffer else None,
            },
            "jsonl": self._jsonl_buffer.get_stats() if self._jsonl_buffer else None,
        }


# 为了向后兼容，保留 DeepLoggingMixin 作为 UnifiedLoggingMixin 的别名
DeepLoggingMixin = UnifiedLoggingMixin

__all__ = [
    "UnifiedLoggingMixin",
    "DeepLoggingMixin",
    "AsyncLogBuffer",
    "JsonlLogBuffer",
    "LogEntry"
]
