"""Deep Runtime - Deep Agent Runtime 模块化 (Mixin 版)

基于 deep-agents 框架的 Runtime 实现，使用 Mixin 模式拆分功能：
- DeepInitializerMixin: 初始化和配置
- DeepMessageHandlerMixin: 消息处理和流式响应
- DeepSkillLoaderMixin: 技能脚本加载
- DeepSandboxMixin: Docker 沙箱代理
- DeepModelSwitcherMixin: 动态模型切换
- DeepCheckpointMixin: Checkpoint 快照
- DeepStopHandlerMixin: 停止处理
- TwoPhaseExecutionMixin: 两阶段执行 (Skill-First → Tool-Fallback)

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
    TwoPhaseExecutionMixin,
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
    TwoPhaseExecutionMixin,
    AbstractAgentRuntime[DeepAgentConfig],
):
    """Deep Agent Runtime 实现 - Mixin 组合版

    集成 Skill Engine 功能：
    - SkillEngineMiddleware: 技能发现、排序、注入
    - TwoPhaseExecution: 两阶段执行策略
    - SkillStore: 技能质量追踪
    - ExecutionAnalyzer: 执行分析
    """

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

        # Skill Engine 组件（延迟初始化）
        self._skill_engine_middleware: Any = None
        self._skill_ranker: Any = None
        self._skill_store: Any = None
        self._execution_analyzer: Any = None
        self._skill_engine_enabled: bool = False

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

    def _init_skill_engine(self) -> None:
        """初始化 Skill Engine 组件

        根据配置初始化：
        - SkillRanker: BM25 + Embedding 技能排序
        - SkillStore: 技能质量追踪
        - SkillEngineMiddleware: 技能注入中间件
        - ExecutionAnalyzer: 执行分析器
        """
        try:
            from backend.infrastructure.config import config as app_config
            from backend.infrastructure.persistence.skill_store import SkillStore
            from backend.infrastructure.runtime.deep.middleware.skill_engine_config import (
                SkillEngineConfig,
            )
            from backend.infrastructure.services.execution_analyzer import (
                ExecutionAnalyzer,
            )
            from backend.infrastructure.services.skill_ranker import SkillRanker

            # 加载 Skill Engine 配置
            skill_config = SkillEngineConfig.from_app_config()

            # 检查功能标志
            if not skill_config.enabled:
                logger.info("[DeepAgentRuntime] Skill Engine disabled by configuration")
                return

            self._skill_engine_enabled = True

            # 初始化 SkillRanker
            if skill_config.embedding.enabled:
                self._skill_ranker = SkillRanker(
                    embedding_enabled=skill_config.embedding.enabled,
                    embedding_model=skill_config.embedding.model,
                )
                logger.info(
                    f"[DeepAgentRuntime] SkillRanker initialized with embedding={skill_config.embedding.enabled}"
                )

            # 初始化 SkillStore
            if skill_config.quality.enabled:
                self._skill_store = SkillStore(
                    data_file=skill_config.quality.data_file,
                )
                logger.info(
                    f"[DeepAgentRuntime] SkillStore initialized with data_file={skill_config.quality.data_file}"
                )

            # 初始化 ExecutionAnalyzer
            self._execution_analyzer = ExecutionAnalyzer()
            logger.info("[DeepAgentRuntime] ExecutionAnalyzer initialized")

            # 配置两阶段执行
            if skill_config.two_phase.enabled:
                from .mixins.two_phase import TwoPhaseConfig

                two_phase_config = TwoPhaseConfig(
                    enabled=True,
                    max_iterations_phase1=15,
                    max_iterations_phase2=20,
                    enable_workspace_cleanup=skill_config.two_phase.cleanup_workspace,
                )
                self.configure_two_phase(two_phase_config)

                # 配置 SkillStore 集成
                if self._skill_store:
                    self.configure_skill_store(
                        skill_store=self._skill_store,
                        task_id=self._agent_id,
                    )

                logger.info(
                    f"[DeepAgentRuntime] Two-phase execution configured: cleanup={skill_config.two_phase.cleanup_workspace}"
                )

            logger.info("[DeepAgentRuntime] Skill Engine initialized successfully")

        except Exception as e:
            logger.error(f"[DeepAgentRuntime] Failed to initialize Skill Engine: {e}")
            self._skill_engine_enabled = False

    def is_skill_engine_enabled(self) -> bool:
        """检查 Skill Engine 是否已启用"""
        return self._skill_engine_enabled

    def get_skill_engine_components(self) -> dict[str, Any]:
        """获取 Skill Engine 组件

        Returns:
            包含 Skill Engine 组件的字典
        """
        return {
            "middleware": self._skill_engine_middleware,
            "ranker": self._skill_ranker,
            "store": self._skill_store,
            "analyzer": self._execution_analyzer,
            "enabled": self._skill_engine_enabled,
        }


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
