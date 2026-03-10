"""Todo 工具注入辅助函数。"""

from typing import TYPE_CHECKING
from loguru import logger

try:
    from agents.base import tool, build_tools_and_handlers
except ImportError:
    from ...base import tool, build_tools_and_handlers

if TYPE_CHECKING:
    from agents.agent.s02_with_skill_loader import S02WithSkillLoaderAgent


def inject_todo_tool(agent: "S02WithSkillLoaderAgent", dialog_id: str) -> None:
    """
    动态注入 todo 工具到 Agent（非侵入式）。

    这允许在不需要修改 S02WithSkillLoaderAgent 类的情况下，
    为 main_new 链路添加 todo 功能。

    Args:
        agent: S02WithSkillLoaderAgent 实例
        dialog_id: 当前对话 ID（用于日志）
    """
    # 检查是否已存在 todo 工具
    for t in agent.tools:
        if t.get("function", {}).get("name") == "todo":
            return  # 已存在，无需注入

    @tool(
        name="todo",
        description="Update task list. Track progress on multi-step tasks. Items have id, text, status (pending/in_progress/completed).",
    )
    def todo_tool(items: list) -> str:
        """Update the todo list with new items."""
        # 简单校验
        if len(items) > 20:
            return "Error: Max 20 todos allowed"

        validated = []
        in_progress_count = 0
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", "")).strip()
            status = str(item.get("status", "pending")).lower()
            item_id = str(item.get("id", str(i + 1)))
            if not text:
                continue
            if status not in ("pending", "in_progress", "completed"):
                status = "pending"
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item_id, "text": text, "status": status})

        if in_progress_count > 1:
            return "Error: Only one task can be in_progress at a time"

        # 返回渲染后的结果
        if not validated:
            return "No todos."
        lines = []
        for item in validated:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[
                item["status"]
            ]
            lines.append(f"{marker} #{item['id']}: {item['text']}")
        done = sum(1 for t in validated if t["status"] == "completed")
        lines.append(f"\n({done}/{len(validated)} completed)")
        return "\n".join(lines)

    # 构建工具定义
    new_tools, new_handlers = build_tools_and_handlers([todo_tool])

    # 注入到 Agent
    agent.tools.extend(new_tools)
    agent.tool_handlers.update(new_handlers)

    logger.debug(f"[inject_todo_tool] Injected todo tool for dialog {dialog_id}")
