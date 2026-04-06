"""
AgentEngine - Agent 核心引擎 (Facade)

基于 Hanako 架构设计思想的门面模式实现。
所有外部交互都通过此类，内部委托给各 Manager。
"""

from typing import Any

from backend.domain.models.shared.config import EngineConfig
from backend.infrastructure.event_bus import EventBus
from backend.infrastructure.logging import get_logger
from backend.infrastructure.plugins import CompactPlugin, PluginManager
from backend.infrastructure.runtime.base.mixins import (
    DialogMixin,
    EventMixin,
    HitlMixin,
    LifecycleMixin,
    MemoryMixin,
    SkillMixin,
    ToolMixin,
)
from backend.infrastructure.services.dialog_manager import DialogManager
from backend.infrastructure.services.memory_manager import MemoryManager
from backend.infrastructure.services.provider_manager import ProviderManager
from backend.infrastructure.services.skill_manager import SkillManager
from backend.infrastructure.services.state_manager import StateManager
from backend.infrastructure.services.tool_manager import ToolManager

logger = get_logger(__name__)


class AgentEngine(
    DialogMixin,
    ToolMixin,
    SkillMixin,
    MemoryMixin,
    EventMixin,
    LifecycleMixin,
    HitlMixin,
):
    """
    Agent 核心引擎 - Facade 模式

    职责:
    - 统一入口，封装内部复杂性
    - 协调各 Manager 工作
    - 提供高级 API 供 Interface 层调用

    使用示例:
        engine = AgentEngine(config)
        await engine.startup()

        # 创建对话
        dialog_id = await engine.create_dialog("Hello")

        # 发送消息
        async for chunk in engine.send_message(dialog_id, "How are you?"):
            print(chunk)

        await engine.shutdown()
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化引擎

        Args:
            config: 配置字典或 EngineConfig
        """
        if isinstance(config, EngineConfig):
            self._config_obj = config
        else:
            self._config_obj = EngineConfig.from_dict(config)
        self._config = config or {}  # 保持向后兼容

        # ═══════════════════════════════════════════════════
        # 初始化基础设施
        # ═══════════════════════════════════════════════════

        # 事件总线 (核心解耦机制)
        self._event_bus = EventBus()

        # ═══════════════════════════════════════════════════
        # 初始化 Managers (依赖注入)
        # ═══════════════════════════════════════════════════

        # 状态管理器
        self._state_mgr = StateManager(config=self._config_obj.state)

        # Provider 管理器
        self._provider_mgr = ProviderManager(config=self._config_obj.provider)

        # 对话管理器
        self._dialog_mgr = DialogManager(
            event_bus=self._event_bus, state_manager=self._state_mgr, config=self._config_obj.dialog
        )

        # 工具管理器
        self._tool_mgr = ToolManager(event_bus=self._event_bus, config=self._config_obj.tools)

        # 记忆管理器
        self._memory_mgr = MemoryManager(event_bus=self._event_bus, config=self._config_obj.memory)

        # 技能管理器
        self._skill_mgr = SkillManager(
            event_bus=self._event_bus, tool_manager=self._tool_mgr, config=self._config_obj.skills
        )

        # 插件管理器
        self._plugin_mgr = PluginManager(self._event_bus)

        # 注册默认插件
        self._plugin_mgr.register(CompactPlugin)

        # 注册插件工具
        for tool in self._plugin_mgr.get_all_tools():
            spec = getattr(tool, "__tool_spec__", {})
            self._tool_mgr.register(
                name=spec.get("name", getattr(tool, "__name__", "")),
                handler=tool,
                description=spec.get("description", ""),
                parameters=spec.get("parameters", {}),
            )

        logger.info("[AgentEngine] Initialized with all managers and plugins")

    @property
    def plugin_manager(self) -> "PluginManager":
        """插件管理器 (高级用例)"""
        return self._plugin_mgr
