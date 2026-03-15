"""
TelemetryService - 遥测服务

职责:
- Token 使用统计
- 延迟指标收集
- 内存使用监控
- 指标聚合与报告
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID, uuid4

from loguru import logger

from ..domain.event import MonitoringEvent, EventType, EventPriority
from ..domain.payloads import (
    TokenUsagePayload,
    MemoryUsagePayload,
    LatencyMetricPayload,
)
from .event_bus import EventBus, event_bus


@dataclass
class TokenMetrics:
    """Token 使用指标"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0

    def add(self, prompt: int, completion: int) -> None:
        """添加一次请求的 token 数据"""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.request_count += 1

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "request_count": self.request_count,
        }


@dataclass
class LatencyMetrics:
    """延迟指标聚合"""
    operation: str
    durations_ms: list[int] = field(default_factory=list)

    def add(self, duration_ms: int) -> None:
        """添加延迟数据点"""
        self.durations_ms.append(duration_ms)

    @property
    def count(self) -> int:
        """数据点数量"""
        return len(self.durations_ms)

    @property
    def avg_ms(self) -> float:
        """平均延迟"""
        if not self.durations_ms:
            return 0.0
        return sum(self.durations_ms) / len(self.durations_ms)

    @property
    def min_ms(self) -> int:
        """最小延迟"""
        if not self.durations_ms:
            return 0
        return min(self.durations_ms)

    @property
    def max_ms(self) -> int:
        """最大延迟"""
        if not self.durations_ms:
            return 0
        return max(self.durations_ms)

    @property
    def p95_ms(self) -> float:
        """95 百分位延迟"""
        if not self.durations_ms:
            return 0.0
        sorted_durations = sorted(self.durations_ms)
        idx = int(len(sorted_durations) * 0.95)
        return float(sorted_durations[min(idx, len(sorted_durations) - 1)])

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "operation": self.operation,
            "count": self.count,
            "avg_ms": round(self.avg_ms, 2),
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "p95_ms": round(self.p95_ms, 2),
        }


@dataclass
class MemoryMetrics:
    """内存使用指标"""
    current_mb: float = 0.0
    peak_mb: float = 0.0
    sample_count: int = 0

    def update(self, used_mb: float) -> None:
        """更新内存使用数据"""
        self.current_mb = used_mb
        self.peak_mb = max(self.peak_mb, used_mb)
        self.sample_count += 1

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "current_mb": round(self.current_mb, 2),
            "peak_mb": round(self.peak_mb, 2),
            "sample_count": self.sample_count,
        }


class TelemetryService:
    """
    遥测服务

    收集和聚合性能指标，支持:
    - Token 使用统计（输入/输出）
    - 操作延迟跟踪
    - 内存使用监控
    - 周期性指标报告

    Example:
        >>> telemetry = TelemetryService(event_bus)
        >>> telemetry.start()
        >>>
        >>> # 记录 token 使用
        >>> telemetry.record_tokens(
        ...     prompt_tokens=100,
        ...     completion_tokens=50,
        ...     model="claude-sonnet-4"
        ... )
        >>>
        >>> # 记录延迟
        >>> telemetry.record_latency("llm_request", 1250)
    """

    def __init__(
        self,
        event_bus: EventBus,
        dialog_id: Optional[str] = None,
        context_id: Optional[UUID] = None,
        report_interval_seconds: float = 60.0,
    ):
        """
        初始化遥测服务

        Args:
            event_bus: 事件总线
            dialog_id: 可选的对话框 ID
            context_id: 可选的上下文 ID
            report_interval_seconds: 报告间隔秒数
        """
        self._event_bus = event_bus
        self._dialog_id = dialog_id or "global"
        self._context_id = context_id or uuid4()
        self._report_interval = report_interval_seconds

        # 指标存储
        self._token_metrics: dict[str, TokenMetrics] = defaultdict(
            lambda: TokenMetrics()
        )
        self._latency_metrics: dict[str, LatencyMetrics] = {}
        self._memory_metrics = MemoryMetrics()

        # 运行状态
        self._running = False
        self._report_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        """启动遥测服务"""
        if self._running:
            return

        self._running = True
        logger.info("[TelemetryService] Started")

        # 启动定期报告任务
        try:
            loop = asyncio.get_running_loop()
            self._report_task = loop.create_task(self._report_loop())
        except RuntimeError:
            logger.warning("[TelemetryService] No event loop, skipping report task")

    def stop(self) -> None:
        """停止遥测服务"""
        self._running = False

        if self._report_task:
            self._report_task.cancel()
            self._report_task = None

        logger.info("[TelemetryService] Stopped")

    def record_tokens(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
    ) -> None:
        """
        记录 Token 使用情况

        Args:
            prompt_tokens: 输入 token 数
            completion_tokens: 输出 token 数
            model: 模型名称
        """
        with self._lock:
            self._token_metrics[model].add(prompt_tokens, completion_tokens)

        # 发送事件
        payload = TokenUsagePayload(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model=model,
        )
        self._emit_event(EventType.TOKEN_USAGE, payload.model_dump())

        logger.debug(
            f"[TelemetryService] Tokens recorded: {prompt_tokens} + "
            f"{completion_tokens} for {model}"
        )

    def record_latency(self, operation: str, duration_ms: int) -> None:
        """
        记录操作延迟

        Args:
            operation: 操作名称
            duration_ms: 耗时毫秒数
        """
        with self._lock:
            if operation not in self._latency_metrics:
                self._latency_metrics[operation] = LatencyMetrics(operation)
            self._latency_metrics[operation].add(duration_ms)

        # 发送事件
        payload = LatencyMetricPayload(
            operation=operation,
            duration_ms=duration_ms,
        )
        self._emit_event(EventType.LATENCY_METRIC, payload.model_dump())

        logger.debug(
            f"[TelemetryService] Latency recorded: {operation} = {duration_ms}ms"
        )

    def record_memory(self, used_mb: float) -> None:
        """
        记录内存使用情况

        Args:
            used_mb: 使用的内存 MB
        """
        with self._lock:
            self._memory_metrics.update(used_mb)

        # 发送事件
        payload = MemoryUsagePayload(
            used_mb=used_mb,
            peak_mb=self._memory_metrics.peak_mb,
        )
        self._emit_event(EventType.MEMORY_USAGE, payload.model_dump())

    def get_token_summary(self) -> dict[str, Any]:
        """获取 Token 使用汇总"""
        with self._lock:
            return {
                model: metrics.to_dict()
                for model, metrics in self._token_metrics.items()
            }

    def get_latency_summary(self) -> dict[str, Any]:
        """获取延迟指标汇总"""
        with self._lock:
            return {
                op: metrics.to_dict()
                for op, metrics in self._latency_metrics.items()
            }

    def get_memory_summary(self) -> dict[str, Any]:
        """获取内存指标汇总"""
        with self._lock:
            return self._memory_metrics.to_dict()

    def get_all_metrics(self) -> dict[str, Any]:
        """获取所有指标汇总"""
        return {
            "tokens": self.get_token_summary(),
            "latency": self.get_latency_summary(),
            "memory": self.get_memory_summary(),
        }

    def reset(self) -> None:
        """重置所有指标"""
        with self._lock:
            self._token_metrics.clear()
            self._latency_metrics.clear()
            self._memory_metrics = MemoryMetrics()

        logger.info("[TelemetryService] Metrics reset")

    async def _report_loop(self) -> None:
        """定期报告循环"""
        while self._running:
            try:
                await asyncio.sleep(self._report_interval)

                if not self._running:
                    break

                await self._emit_summary_event()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[TelemetryService] Report error: {e}")

    async def _emit_summary_event(self) -> None:
        """发送指标汇总事件"""
        metrics = self.get_all_metrics()

        event = MonitoringEvent(
            type=EventType.LATENCY_METRIC,  # 使用通用指标类型
            dialog_id=self._dialog_id,
            source="TelemetryService",
            context_id=self._context_id,
            priority=EventPriority.LOW,
            payload={
                "metrics_type": "summary",
                "data": metrics,
            },
        )

        try:
            await self._event_bus.emit(event)
        except Exception as e:
            logger.error(f"[TelemetryService] Failed to emit summary: {e}")

    def _emit_event(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """发送事件"""
        event = MonitoringEvent(
            type=event_type,
            dialog_id=self._dialog_id,
            source="TelemetryService",
            context_id=self._context_id,
            priority=EventPriority.LOW,
            payload=payload,
        )

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._event_bus.emit(event))
        except RuntimeError:
            pass  # 无事件循环时静默失败


# 全局遥测服务实例
_telemetry_instance: Optional[TelemetryService] = None


def get_telemetry_service(
    event_bus_arg: Optional[EventBus] = None,
    dialog_id: Optional[str] = None,
) -> TelemetryService:
    """
    获取全局遥测服务实例

    Args:
        event_bus_arg: 事件总线（首次创建时需要）
        dialog_id: 对话框 ID

    Returns:
        TelemetryService 实例
    """
    global _telemetry_instance

    if _telemetry_instance is None:
        bus = event_bus_arg if event_bus_arg is not None else event_bus
        _telemetry_instance = TelemetryService(bus, dialog_id)

    return _telemetry_instance


def reset_telemetry_service() -> None:
    """重置全局遥测服务实例"""
    global _telemetry_instance
    _telemetry_instance = None
