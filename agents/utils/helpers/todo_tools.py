"""Todo 工具注入辅助函数。"""

import json
import re
from typing import Any
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
    def todo_tool(items: Any) -> str:
        """Update the todo list with new items."""
        max_items = 20

        def _extract_items_from_obj(data: Any) -> list[dict[str, Any]] | None:
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("items", "todoList", "todos", "tasks", "data"):
                    value = data.get(key)
                    if isinstance(value, list):
                        return value
            return None

        def _parse_json_items_text(text: str) -> list[dict[str, Any]] | None:
            raw = str(text).strip()
            if not raw:
                return None
            try:
                parsed = json.loads(raw)
            except Exception:
                return None
            return _extract_items_from_obj(parsed)

        def _parse_text_items(text: str) -> list[dict[str, str]]:
            parsed: list[dict[str, str]] = []
            for idx, raw_line in enumerate(str(text).splitlines(), start=1):
                line = raw_line.strip()
                if not line:
                    continue
                line = re.sub(r"^\d+[\.)]\s*", "", line)
                line = re.sub(r"^[-*]\s*", "", line)
                if not line:
                    continue
                parsed.append({"id": str(idx), "text": line, "status": "pending"})
            return parsed

        # 兼容 list/dict/string 三类输入，避免因模型参数漂移导致报错。
        if isinstance(items, list):
            raw_items = items
        elif isinstance(items, dict):
            for key in ("items", "todoList", "todos", "tasks", "data"):
                if isinstance(items.get(key), list):
                    raw_items = items[key]
                    break
                if isinstance(items.get(key), str):
                    raw_items = _parse_json_items_text(items[key]) or _parse_text_items(items[key])
                    break
            else:
                raw_items = []
        elif isinstance(items, str):
            raw_items = _parse_json_items_text(items) or _parse_text_items(items)
        else:
            raw_items = []

        validated = []
        for i, item in enumerate(raw_items):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", "")).strip()
            status = str(item.get("status", "pending")).lower()
            item_id = str(item.get("id", str(i + 1)))
            if not text:
                continue
            if status not in ("pending", "in_progress", "completed"):
                status = "pending"
            validated.append({"id": item_id, "text": text, "status": status})

        truncated = False
        if len(validated) > max_items:
            validated = validated[:max_items]
            truncated = True

        # 降级策略：多条 in_progress 时保留第一条，其余降级为 pending。
        seen_in_progress = False
        for item in validated:
            if item["status"] != "in_progress":
                continue
            if not seen_in_progress:
                seen_in_progress = True
            else:
                item["status"] = "pending"

        # 返回渲染后的结果
        if not validated:
            return json.dumps({"items": []}, ensure_ascii=False)

        done = sum(1 for t in validated if t["status"] == "completed")
        payload = {
            "items": validated,
            "meta": {
                "completed": done,
                "total": len(validated),
                "truncated": truncated,
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    # 构建工具定义
    new_tools, new_handlers = build_tools_and_handlers([todo_tool])
    todo_tool_schema = new_tools[0]

    # 将 todo 排在 loader 工具后面，保证工具展示/选择顺序稳定。
    loader_names = {"load_skill", "load_skill_reference", "load_skill_script"}
    insert_after_idx = -1
    for idx, tool_schema in enumerate(agent.tools):
        name = tool_schema.get("function", {}).get("name")
        if name in loader_names:
            insert_after_idx = idx

    # 注入到 Agent
    if insert_after_idx >= 0:
        agent.tools.insert(insert_after_idx + 1, todo_tool_schema)
    else:
        agent.tools.append(todo_tool_schema)

    agent.tool_handlers.update(new_handlers)

    logger.debug(f"[inject_todo_tool] Injected todo tool for dialog {dialog_id}")
