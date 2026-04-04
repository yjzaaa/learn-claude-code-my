"""Runtime Mixins - 可复用的 Runtime 功能组件

提供可组合的功能模块，通过 Mixin 模式减少代码重复。
"""

from typing import Any, Callable, Coroutine, List, Optional, TYPE_CHECKING

from core.hitl import (
    skill_edit_hitl_store, todo_store,
    is_skill_edit_hitl_enabled, is_todo_hook_enabled
)
from core.models.api import DecisionResult, TodoStateDTO

if TYPE_CHECKING:
    from runtime.event_bus import EventBus
    from core.managers.dialog_manager import DialogManager
    from core.managers.tool_manager import ToolManager
    from core.managers.memory_manager import MemoryManager
    from core.managers.skill_manager import SkillManager
    from core.managers.provider_manager import ProviderManager
    from core.managers.state_manager import StateManager


class HITLAPIMixin:
    """HITL API Mixin - 提供 Skill Edit 和 Todo 管理功能

    可被任何需要 HITL 功能的 Runtime 继承。
    """

    def get_skill_edit_proposals(self, dialog_id: Optional[str] = None) -> list[dict]:
        """获取待处理的 Skill 编辑提案"""
        if not is_skill_edit_hitl_enabled():
            return []
        return skill_edit_hitl_store.list_pending(dialog_id)

    def decide_skill_edit(
        self,
        approval_id: str,
        decision: str,
        edited_content: Optional[str] = None
    ) -> DecisionResult:
        """处理 Skill 编辑审核决定"""
        if not is_skill_edit_hitl_enabled():
            return DecisionResult(success=False, message="HITL disabled")
        return skill_edit_hitl_store.decide(approval_id, decision, edited_content)

    def get_todos(self, dialog_id: str) -> TodoStateDTO:
        """获取对话的 Todo 列表"""
        if not is_todo_hook_enabled():
            return TodoStateDTO(
                dialog_id=dialog_id,
                items=[],
                rounds_since_todo=0,
                updated_at=0.0
            )
        return todo_store.get_todos(dialog_id)

    def update_todos(self, dialog_id: str, items: list[dict]) -> tuple[bool, str]:
        """更新对话的 Todo 列表"""
        if not is_todo_hook_enabled():
            return False, "Todo HITL disabled"
        return todo_store.update_todos(dialog_id, items)

    def register_hitl_broadcaster(
        self,
        broadcaster: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        """注册 HITL 广播器"""
        if is_skill_edit_hitl_enabled():
            skill_edit_hitl_store.register_broadcaster(broadcaster)
        if is_todo_hook_enabled():
            todo_store.register_broadcaster(broadcaster)


class ManagerAccessMixin:
    """Manager 访问 Mixin - 提供标准 Manager 属性访问器

    要求子类初始化以下属性：
    - _event_bus: EventBus
    - _state_mgr: StateManager
    - _dialog_mgr: DialogManager
    - _tool_mgr: ToolManager
    - _memory_mgr: MemoryManager
    - _skill_mgr: SkillManager
    - _provider_mgr: ProviderManager
    """

    # Type annotations for attributes expected from child classes
    _event_bus: "EventBus"
    _state_mgr: "StateManager"
    _dialog_mgr: "DialogManager"
    _tool_mgr: "ToolManager"
    _memory_mgr: "MemoryManager"
    _skill_mgr: "SkillManager"
    _provider_mgr: "ProviderManager"

    @property
    def event_bus(self):
        """事件总线（高级用例）"""
        return self._event_bus

    @property
    def dialog_manager(self):
        """对话管理器（高级用例）"""
        return self._dialog_mgr

    @property
    def tool_manager(self):
        """工具管理器（高级用例）"""
        return self._tool_mgr

    @property
    def memory_manager(self):
        """记忆管理器（高级用例）"""
        return self._memory_mgr

    @property
    def skill_manager(self):
        """技能管理器（高级用例）"""
        return self._skill_mgr

    @property
    def provider_manager(self):
        """Provider 管理器（高级用例）"""
        return self._provider_mgr

    @property
    def state_manager(self):
        """状态管理器（高级用例）"""
        return self._state_mgr


class SkillManagementMixin:
    """技能管理 Mixin - 提供技能加载和列表功能

    要求子类初始化 _skill_mgr: SkillManager
    """

    _skill_mgr: "SkillManager"

    def load_skill(self, skill_path: str) -> Optional[Any]:
        """加载技能"""
        return self._skill_mgr.load_skill_from_directory(skill_path)

    def list_skills(self) -> List[Any]:
        """列出所有技能"""
        return self._skill_mgr.list_skills()


class MemoryManagementMixin:
    """记忆管理 Mixin - 提供 memory.md 访问功能

    要求子类初始化 _memory_mgr: MemoryManager
    """

    _memory_mgr: "MemoryManager"

    def get_memory(self) -> str:
        """读取 memory.md 内容"""
        return self._memory_mgr.load_memory()  # type: ignore[attr-defined]


class EventManagementMixin:
    """事件管理 Mixin - 提供事件订阅和发射功能

    要求子类初始化 _event_bus: EventBus
    """

    _event_bus: "EventBus"

    def subscribe(
        self,
        callback: Callable,
        event_types: Optional[List[str]] = None,
        dialog_id: Optional[str] = None
    ) -> Callable:
        """订阅事件"""
        return self._event_bus.subscribe(callback, event_types, dialog_id)

    def emit(self, event: Any) -> None:
        """发射事件"""
        self._event_bus.emit(event)


class ManagerLifecycleMixin:
    """Manager 生命周期管理 Mixin

    要求子类初始化以下属性：
    - _event_bus: EventBus
    - _state_mgr: StateManager
    """

    _event_bus: "EventBus"
    _state_mgr: "StateManager"

    async def _load_state(self) -> None:
        """加载持久化状态"""
        await self._state_mgr.load()  # type: ignore[attr-defined]

    async def _save_state(self) -> None:
        """保存状态到持久化存储"""
        await self._state_mgr.save()  # type: ignore[attr-defined]

    def _emit_system_started(self) -> None:
        """发射系统启动事件"""
        from core.models.events import SystemStarted
        self._event_bus.emit(SystemStarted())  # type: ignore[attr-defined]

    def _emit_system_stopped(self) -> None:
        """发射系统停止事件"""
        from core.models.events import SystemStopped
        self._event_bus.emit(SystemStopped())  # type: ignore[attr-defined]

    def _shutdown_event_bus(self) -> None:
        """关闭事件总线"""
        self._event_bus.shutdown()  # type: ignore[attr-defined]


__all__ = [
    "HITLAPIMixin",
    "ManagerAccessMixin",
    "SkillManagementMixin",
    "MemoryManagementMixin",
    "EventManagementMixin",
    "ManagerLifecycleMixin",
]