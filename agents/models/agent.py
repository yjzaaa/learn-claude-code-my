"""
代理相关数据模型
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class AgentType(str, Enum):
    """代理类型 - 与前端 AgentType 对齐"""
    MASTER = "master"
    SQL_EXECUTOR = "sql_executor"
    SCHEMA_EXPLORER = "schema_explorer"
    DATA_VALIDATOR = "data_validator"
    ANALYZER = "analyzer"
    SKILL_LOADER = "skill_loader"
    DEFAULT = "default"


class AgentState:
    """
    Agent 运行状态

    封装 is_running, stop_requested 等状态管理
    """

    def __init__(self):
        self._is_running: bool = False
        self._stop_requested: bool = False
        self._current_dialog_id: Optional[str] = None
        self._current_agent_type: Optional[str] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def stop_requested(self) -> bool:
        return self._stop_requested

    @property
    def current_dialog_id(self) -> Optional[str]:
        return self._current_dialog_id

    @property
    def current_agent_type(self) -> Optional[str]:
        return self._current_agent_type

    def start(self, dialog_id: str, agent_type: str = "default") -> None:
        """开始运行"""
        self._is_running = True
        self._stop_requested = False
        self._current_dialog_id = dialog_id
        self._current_agent_type = agent_type

    def stop(self) -> None:
        """请求停止"""
        self._stop_requested = True

    def reset(self) -> None:
        """重置状态"""
        self._is_running = False
        self._stop_requested = False
        self._current_dialog_id = None
        self._current_agent_type = None

    def check_should_stop(self) -> bool:
        """检查是否应该停止"""
        return self._stop_requested

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "is_running": self._is_running,
            "stop_requested": self._stop_requested,
            "current_dialog_id": self._current_dialog_id,
            "current_agent_type": self._current_agent_type,
        }
