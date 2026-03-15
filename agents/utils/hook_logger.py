"""
Hook Logger - 专用日志工具

将 hook 层的关键数据写入 .logs 目录的 jsonl 文件中，便于调试和追踪。
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from loguru import logger
from pydantic import BaseModel


class HistoryRebuildEntry(BaseModel):
    """历史重建日志条目"""
    timestamp: float
    datetime: str
    event_type: str
    dialog_id: str | None = None
    history_rounds_count: int
    history_rounds: list[dict[str, str]]
    pending_round: dict[str, str] | None
    window_rounds: int
    result_messages_count: int
    result_messages: list[dict[str, Any]]
    extra: dict[str, Any] | None = None


class HookEventEntry(BaseModel):
    """Hook 事件日志条目"""
    timestamp: float
    datetime: str
    event_type: str
    dialog_id: str | None = None
    hook_name: str | None = None
    data: dict[str, Any]


class MessageLogEntry(BaseModel):
    """消息操作日志条目"""
    timestamp: float
    datetime: str
    event_type: str
    dialog_id: str | None = None
    action: str
    message: dict[str, Any]


class ToolCallLogEntry(BaseModel):
    """工具调用日志条目"""
    timestamp: float
    datetime: str
    event_type: str
    dialog_id: str | None = None
    tool_name: str
    arguments: dict[str, Any]
    result: Any | None = None
    status: str


class HookLogger:
    """Hook 层专用日志记录器"""

    _instance: Optional["HookLogger"] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, logs_dir: str | Path | None = None):
        if HookLogger._initialized:
            return

        self._logs_dir = Path(logs_dir) if logs_dir else Path.cwd() / ".logs"
        self._logs_dir.mkdir(parents=True, exist_ok=True)

        # 不同用途的日志文件
        self._history_log = self._logs_dir / "history_rebuild.jsonl"
        self._hook_events_log = self._logs_dir / "hook_events.jsonl"
        self._messages_log = self._logs_dir / "messages.jsonl"

        HookLogger._initialized = True
        logger.info(f"[HookLogger] Initialized, logs dir: {self._logs_dir}")

    def _write_jsonl(self, log_file: Path, data: dict[str, Any]) -> None:
        """将数据写入 jsonl 文件"""
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            logger.error(f"[HookLogger] Failed to write to {log_file}: {e}")

    def log_history_rebuild(
        self,
        dialog_id: str,
        history_rounds: list[dict[str, str]],
        pending_round: dict[str, str] | None,
        window_rounds: int,
        result_messages: list[dict[str, Any]],
        **extra: Any
    ) -> None:
        """
        记录历史消息重建过程

        Args:
            dialog_id: 对话 ID
            history_rounds: 历史轮次列表
            pending_round: 待处理的当前轮次
            window_rounds: 窗口大小
            result_messages: 最终构建的消息列表
            **extra: 额外数据
        """
        entry = HistoryRebuildEntry(
            timestamp=time.time(),
            datetime=datetime.now().isoformat(),
            event_type="history_rebuild",
            dialog_id=dialog_id,
            history_rounds_count=len(history_rounds),
            history_rounds=history_rounds,
            pending_round=pending_round,
            window_rounds=window_rounds,
            result_messages_count=len(result_messages),
            result_messages=result_messages,
            extra=extra if extra else None,
        )

        self._write_jsonl(self._history_log, entry.model_dump())
        logger.debug(f"[HookLogger] History rebuild logged for dialog {dialog_id}")

    def log_hook_event(
        self,
        event_type: str,
        dialog_id: str | None = None,
        hook_name: str | None = None,
        data: dict[str, Any] | None = None
    ) -> None:
        """
        记录 hook 事件

        Args:
            event_type: 事件类型 (on_start/on_stop/on_tool_call 等)
            dialog_id: 对话 ID
            hook_name: Hook 名称
            data: 事件数据
        """
        entry = HookEventEntry(
            timestamp=time.time(),
            datetime=datetime.now().isoformat(),
            event_type=event_type,
            dialog_id=dialog_id,
            hook_name=hook_name,
            data=data or {},
        )

        self._write_jsonl(self._hook_events_log, entry.model_dump())

    def log_message(
        self,
        dialog_id: str,
        message: dict[str, Any],
        action: str = "add"
    ) -> None:
        """
        记录消息操作

        Args:
            dialog_id: 对话 ID
            message: 消息内容
            action: 操作类型 (add/update/delete)
        """
        entry = MessageLogEntry(
            timestamp=time.time(),
            datetime=datetime.now().isoformat(),
            event_type="message",
            dialog_id=dialog_id,
            action=action,
            message=message,
        )

        self._write_jsonl(self._messages_log, entry.model_dump())

    def log_tool_call(
        self,
        dialog_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any | None = None,
        status: str = "started"
    ) -> None:
        """
        记录工具调用

        Args:
            dialog_id: 对话 ID
            tool_name: 工具名称
            arguments: 工具参数
            result: 调用结果
            status: 状态 (started/completed/failed)
        """
        entry = ToolCallLogEntry(
            timestamp=time.time(),
            datetime=datetime.now().isoformat(),
            event_type="tool_call",
            dialog_id=dialog_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            status=status,
        )

        self._write_jsonl(self._hook_events_log, entry.model_dump())

    def get_logs_summary(self) -> dict[str, int]:
        """获取日志文件摘要统计"""
        return {
            "history_rebuild": self._count_lines(self._history_log),
            "hook_events": self._count_lines(self._hook_events_log),
            "messages": self._count_lines(self._messages_log),
        }

    def _count_lines(self, file_path: Path) -> int:
        """统计文件行数"""
        if not file_path.exists():
            return 0
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0


# 全局实例
hook_logger = HookLogger()


def get_hook_logger() -> HookLogger:
    """获取 HookLogger 实例"""
    return hook_logger
