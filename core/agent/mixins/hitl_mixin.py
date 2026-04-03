"""
HITL (Human-in-the-Loop) 相关功能的 Mixin
"""

from typing import Callable, Any

from core.hitl import (
    skill_edit_hitl_store,
    todo_store,
    is_skill_edit_hitl_enabled,
    is_todo_hook_enabled,
)
from core.models.api import DecisionResult, TodoStateDTO
from .base import EngineMixinBase


class HitlMixin(EngineMixinBase):
    """HITL 功能"""

    # Skill Edit HITL
    def get_skill_edit_proposals(self, dialog_id: str | None = None) -> list[dict]:
        """获取待处理的 Skill 编辑提案"""
        if not is_skill_edit_hitl_enabled():
            return []
        return skill_edit_hitl_store.list_pending(dialog_id)

    def decide_skill_edit(self, approval_id: str, decision: str, edited_content: str | None = None) -> DecisionResult:
        """处理 Skill 编辑审核决定"""
        if not is_skill_edit_hitl_enabled():
            return DecisionResult(success=False, message="HITL disabled")
        return skill_edit_hitl_store.decide(approval_id, decision, edited_content)

    # Todo HITL
    def get_todos(self, dialog_id: str) -> TodoStateDTO:
        """获取对话的 Todo 列表"""
        if not is_todo_hook_enabled():
            return TodoStateDTO(dialog_id=dialog_id, items=[], rounds_since_todo=0, updated_at=0.0)
        return todo_store.get_todos(dialog_id)

    def update_todos(self, dialog_id: str, items: list[dict]) -> tuple[bool, str]:
        """更新对话的 Todo 列表"""
        if not is_todo_hook_enabled():
            return False, "Todo HITL disabled"
        return todo_store.update_todos(dialog_id, items)

    def register_hitl_broadcaster(self, broadcaster: Callable[[dict[str, Any]], None]) -> None:
        """注册 HITL 广播器"""
        if is_skill_edit_hitl_enabled():
            skill_edit_hitl_store.register_broadcaster(broadcaster)
        if is_todo_hook_enabled():
            todo_store.register_broadcaster(broadcaster)
