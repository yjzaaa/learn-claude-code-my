"""Deep Runtime - Deep Agent Runtime 模块化 (Mixin 版)

基于 deep-agents 框架的 Runtime 实现，使用 Mixin 模式拆分功能：
- DeepInitializerMixin: 初始化和配置
- DeepMessageHandlerMixin: 消息处理和流式响应
- DeepSkillLoaderMixin: 技能脚本加载
- DeepSandboxMixin: Docker 沙箱代理
- DeepModelSwitcherMixin: 动态模型切换
- DeepCheckpointMixin: Checkpoint 快照
- DeepStopHandlerMixin: 停止处理

保持与 deep_legacy.py 100% API 兼容。
"""

from typing import Any, Optional

from loguru import logger

from backend.infrastructure.llm_adapter import LLMResponseAdapterFactory

from ..base.runtime import AbstractAgentRuntime
from .mixins import (
    DeepCheckpointMixin,
    DeepInitializerMixin,
    DeepMessageHandlerMixin,
    DeepModelSwitcherMixin,
    DeepSandboxMixin,
    DeepSkillLoaderMixin,
    DeepStopHandlerMixin,
)
from .services.config_adapter import DeepAgentConfig
from .services.logging_mixin import DeepLoggingMixin


class DeepAgentRuntime(
    DeepLoggingMixin,
    DeepInitializerMixin,
    DeepMessageHandlerMixin,
    DeepSkillLoaderMixin,
    DeepSandboxMixin,
    DeepModelSwitcherMixin,
    DeepCheckpointMixin,
    DeepStopHandlerMixin,
    AbstractAgentRuntime[DeepAgentConfig],
):
    """Deep Agent Runtime 实现 - Mixin 组合版"""

    def __init__(self, agent_id: str, provider_manager: Any | None = None):
        DeepLoggingMixin.__init__(self)
        AbstractAgentRuntime.__init__(self, agent_id)
        self._agent: Any = None
        self._checkpointer: Any = None
        self._store: Any = None
        self._model_name: str | None = None
        self._provider_manager = provider_manager
        self._adapter_factory = LLMResponseAdapterFactory()
        self._stop_requested: dict[str, bool] = {}  # Used by DeepStopHandlerMixin

        logger.debug(f"[DeepAgentRuntime] Created: {agent_id}")

    @property
    def agent_type(self) -> str:
        return "deep"

    @property
    def session_manager(self):
        """获取 SessionManager 实例"""
        return getattr(self, "_session_mgr", None)

    def set_session_manager(self, mgr):
        """设置 SessionManager 实例"""
        self._session_mgr = mgr


__all__ = [
    "DeepAgentRuntime",
    "DeepAgentConfig",
    # Mixin classes
    "DeepInitializerMixin",
    "DeepMessageHandlerMixin",
    "DeepSkillLoaderMixin",
    "DeepSandboxMixin",
    "DeepModelSwitcherMixin",
    "DeepCheckpointMixin",
    "DeepStopHandlerMixin",
]
