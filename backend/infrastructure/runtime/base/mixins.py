"""
Runtime Mixins - 可复用的 Runtime 功能组件

提供可组合的功能模块，通过 Mixin 模式减少代码重复。
"""

from abc import ABC
from typing import Any


class ManagerLifecycleMixin(ABC):
    """
    Manager 生命周期 Mixin

    提供统一的 Manager 初始化和清理逻辑。
    适用于需要完整 Manager 集成的 Runtime。
    """

    _dialog_mgr: Any | None = None
    _tool_mgr: Any | None = None
    _state_mgr: Any | None = None
    _provider_mgr: Any | None = None
    _memory_mgr: Any | None = None
    _skill_mgr: Any | None = None

    def _initialize_managers_lifecycle(self) -> None:
        """初始化所有 Manager 的引用"""
        pass

    def _cleanup_managers(self) -> None:
        """清理所有 Manager 资源"""
        if self._dialog_mgr:
            self._dialog_mgr = None
        if self._tool_mgr:
            self._tool_mgr = None
        if self._state_mgr:
            self._state_mgr = None
        if self._provider_mgr:
            self._provider_mgr = None
        if self._memory_mgr:
            self._memory_mgr = None
        if self._skill_mgr:
            self._skill_mgr = None


class EventMixin:
    """Event Mixin - 事件相关功能"""

    _event_bus: Any = None

    def _emit_system_started(self) -> None:
        """发射系统启动事件"""
        pass

    def _emit_system_stopped(self) -> None:
        """发射系统停止事件"""
        pass

    def _shutdown_event_bus(self) -> None:
        """关闭事件总线"""
        if self._event_bus:
            self._event_bus.stop()


class MemoryMixin:
    """Memory Mixin - 记忆管理功能"""

    _memory_mgr: Any = None

    def _load_memory(self) -> str:
        """加载长期记忆"""
        if self._memory_mgr:
            return self._memory_mgr.load_memory()
        return ""

    def _save_memory(self, content: str) -> None:
        """保存长期记忆"""
        if self._memory_mgr:
            self._memory_mgr.save_memory(content)


class SkillMixin:
    """Skill Mixin - 技能管理功能"""

    _skill_mgr: Any = None

    def _load_skill_scripts(self) -> None:
        """加载技能脚本"""
        pass


class ToolMixin:
    """Tool Mixin - 工具管理功能"""

    _tool_mgr: Any = None

    def _adapt_tools(self, tools: dict[str, Any]) -> list[Any]:
        """转换工具格式"""
        return []


class LifecycleMixin:
    """Lifecycle Mixin - 生命周期管理"""

    async def _do_initialize(self) -> None:
        """子类实现: 特定初始化逻辑"""
        pass

    async def _do_shutdown(self) -> None:
        """子类实现: 特定清理逻辑"""
        pass


class HitlMixin:
    """HITL Mixin - 人机交互功能"""

    def get_skill_edit_proposals(self, dialog_id: str | None = None) -> list[Any]:
        """获取待处理的 Skill 编辑提案"""
        return []

    def decide_skill_edit(
        self, approval_id: str, decision: str, edited_content: str | None = None
    ) -> Any:
        """处理 Skill 编辑审核决定"""
        pass


class DialogMixin:
    """Dialog Mixin - 对话管理功能"""

    _dialog_mgr: Any = None
    _session_mgr: Any = None

    async def create_dialog(self, user_input: str, title: str | None = None) -> str:
        """创建对话"""
        import uuid

        return str(uuid.uuid4())


__all__ = [
    "ManagerLifecycleMixin",
    "EventMixin",
    "MemoryMixin",
    "SkillMixin",
    "ToolMixin",
    "LifecycleMixin",
    "HitlMixin",
    "DialogMixin",
]
