"""
Mixin 基类 - 声明 Engine 的所有属性，用于类型提示
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from runtime.event_bus import EventBus
    from core.managers.dialog_manager import DialogManager
    from core.managers.tool_manager import ToolManager
    from core.managers.state_manager import StateManager
    from core.managers.provider_manager import ProviderManager
    from core.managers.memory_manager import MemoryManager
    from core.managers.skill_manager import SkillManager
    from core.plugins import PluginManager
    from core.models.config import EngineConfig


class EngineMixinBase:
    """Mixin 基类，声明 Engine 的所有属性"""

    # 配置
    _config: dict[str, Any]
    _config_obj: "EngineConfig"

    # Managers
    _event_bus: "EventBus"
    _state_mgr: "StateManager"
    _provider_mgr: "ProviderManager"
    _dialog_mgr: "DialogManager"
    _tool_mgr: "ToolManager"
    _memory_mgr: "MemoryManager"
    _skill_mgr: "SkillManager"
    _plugin_mgr: "PluginManager"
