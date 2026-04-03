"""
AgentEngine - Agent 核心引擎 (Facade)

基于 Hanako 架构设计思想的门面模式实现。
所有外部交互都通过此类，内部委托给各 Manager。
"""

from typing import Any
import logging

from runtime.event_bus import EventBus
from core.managers.dialog_manager import DialogManager
from core.managers.tool_manager import ToolManager
from core.managers.state_manager import StateManager
from core.managers.provider_manager import ProviderManager
from core.managers.memory_manager import MemoryManager
from core.managers.skill_manager import SkillManager
from core.models.config import EngineConfig
from core.plugins import PluginManager, CompactPlugin
from core.agent.mixins import (
    EventMixin,
    MemoryMixin,
    SkillMixin,
    ToolMixin,
    LifecycleMixin,
    HitlMixin,
    DialogMixin,
)

logger = logging.getLogger(__name__)


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
        self._state_mgr = StateManager(
            config=self._config_obj.state
        )

        # Provider 管理器
        self._provider_mgr = ProviderManager(
            config=self._config_obj.provider
        )

        # 对话管理器
        self._dialog_mgr = DialogManager(
            event_bus=self._event_bus,
            state_manager=self._state_mgr,
            config=self._config_obj.dialog
        )

        # 工具管理器
        self._tool_mgr = ToolManager(
            event_bus=self._event_bus,
            config=self._config_obj.tools
        )

        # 记忆管理器
        self._memory_mgr = MemoryManager(
            event_bus=self._event_bus,
            config=self._config_obj.memory
        )

        # 技能管理器
        self._skill_mgr = SkillManager(
            event_bus=self._event_bus,
            tool_manager=self._tool_mgr,
            config=self._config_obj.skills
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
                parameters=spec.get("parameters", {})
            )

        logger.info("[AgentEngine] Initialized with all managers and plugins")

    @property
    def plugin_manager(self) -> "PluginManager":
        """插件管理器 (高级用例)"""
        return self._plugin_mgr
