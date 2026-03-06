"""Composed SQL agent loop: s05 skills + s03 todo behavior."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

try:
    from .base import BaseAgentLoop, tool
    from .s05_skill_loading import SYSTEM as S05_SYSTEM, TOOLS as S05_TOOLS
except ImportError:
    from agents.base import BaseAgentLoop, tool
    from agents.s05_skill_loading import SYSTEM as S05_SYSTEM, TOOLS as S05_TOOLS


_TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FORBIDDEN_SQL = ("drop ", "truncate ", "alter ", "create ", "exec ", "xp_")


class TodoManager:
    """In-memory todo tracker adapted from s03_todo_write."""

    def __init__(self):
        self.items: list[dict[str, str]] = []

    def update(self, items: list) -> str:
        if len(items) > 20:
            raise ValueError("Max 20 todos allowed")

        validated: list[dict[str, str]] = []
        in_progress_count = 0
        for idx, item in enumerate(items):
            item_id = str(item.get("id", str(idx + 1))).strip()
            text = str(item.get("text", "")).strip()
            status = str(item.get("status", "pending")).lower().strip()

            if not text:
                raise ValueError(f"Item {item_id}: text required")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Item {item_id}: invalid status '{status}'")
            if status == "in_progress":
                in_progress_count += 1

            validated.append({"id": item_id, "text": text, "status": status})

        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress at a time")

        self.items = validated
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "No todos."

        marker_map = {
            "pending": "[ ]",
            "in_progress": "[>]",
            "completed": "[x]",
        }
        lines: list[str] = []
        for item in self.items:
            marker = marker_map.get(item["status"], "[?]")
            lines.append(f"{marker} #{item['id']}: {item['text']}")

        done_count = sum(1 for item in self.items if item["status"] == "completed")
        lines.append(f"\n({done_count}/{len(self.items)} completed)")
        return "\n".join(lines)


def _get_sql_runner():
    """Resolve SQL execution backend used by generic SQL tools."""
    from skills.finance.scripts.sql_query import run_sql_query

    return run_sql_query


_TODO = TodoManager()


@tool(name="todo", description="Update task checklist for multi-step execution progress.")
def todo(items: list) -> str:
    return _TODO.update(items)


@tool(name="sql_execute", description="Execute SQL and return query result JSON or execution status.")
def sql_execute(sql: str, limit: int = 200) -> str:
    run_sql_query = _get_sql_runner()
    return run_sql_query(sql, limit=max(1, min(int(limit), 2000)))


@tool(name="sql_validate", description="Validate SQL text for basic syntax safety before execution.")
def sql_validate(sql: str, allow_ddl: bool = False) -> str:
    text = (sql or "").strip()
    if not text:
        return json.dumps({"ok": False, "errors": ["SQL is empty"]}, ensure_ascii=False)

    errors: list[str] = []
    warnings: list[str] = []

    if text.count("(") != text.count(")"):
        errors.append("Unbalanced parentheses")
    if text.count("[") != text.count("]"):
        errors.append("Unbalanced SQL Server identifier brackets []")
    if text.count("'") % 2 != 0:
        errors.append("Unbalanced single quotes")
    if not text.endswith(";"):
        warnings.append("SQL does not end with semicolon")

    lowered = text.lower()
    if not allow_ddl:
        blocked = [kw.strip() for kw in _FORBIDDEN_SQL if kw in lowered]
        if blocked:
            errors.append(f"Potentially destructive keyword detected: {', '.join(blocked)}")

    return json.dumps(
        {
            "ok": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        },
        ensure_ascii=False,
    )


@tool(name="sql_describe_table", description="Query table schema and sample rows by table name.")
def sql_describe_table(table_name: str, sample_limit: int = 5) -> str:
    run_sql_query = _get_sql_runner()

    table = (table_name or "").strip()
    if not table:
        return "Error: table_name is required"
    if not _TABLE_NAME_PATTERN.match(table):
        return "Error: invalid table_name"

    safe_limit = max(1, min(int(sample_limit), 50))
    schema_sql = (
        "SELECT COLUMN_NAME, DATA_TYPE "
        "FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_NAME = '{table}'"
    )
    sample_sql = f"SELECT TOP {safe_limit} * FROM {table}"

    schema_result = run_sql_query(schema_sql, limit=500)
    sample_result = run_sql_query(sample_sql, limit=safe_limit)

    return json.dumps(
        {
            "table": table,
            "schema": _try_parse_json(schema_result),
            "sample": _try_parse_json(sample_result),
        },
        ensure_ascii=False,
    )


SQL_WORKFLOW_CONSTRAINT = """
[SQL workflow constraint]
- You MUST obtain candidate table names from the loaded skill workflow/context first.
- Do NOT enumerate or scan all database tables as a first step.
- If SQL fails due to invalid object name, re-check skill-provided table references and retry with corrected table names.
- Only ask user to confirm table name after at least one skill-guided retry attempt.
""".strip()

TODO_WORKFLOW_CONSTRAINT = """
[Todo workflow constraint]
- For multi-step work, you MUST maintain a todo list via the `todo` tool.
- Mark exactly one item as in_progress while executing, and mark it completed when done.
- Keep todo list concise and status-accurate after each major step.
""".strip()

TODO_REMINDER_POLICY = """
[Todo reminder policy]
- If you proceed several rounds without updating todo for a multi-step task, you must update it before continuing.
""".strip()

SYSTEM = (
    f"{S05_SYSTEM}\n\n"
    f"{SQL_WORKFLOW_CONSTRAINT}\n\n"
    f"{TODO_WORKFLOW_CONSTRAINT}\n\n"
    f"{TODO_REMINDER_POLICY}"
)
TOOLS = list(S05_TOOLS) + [
    todo,
    sql_execute,
    sql_validate,
    sql_describe_table,
]


class SQLAgentLoop(BaseAgentLoop):
    """Composable agent loop that merges s05 and s03 behaviors."""

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        system: str = SYSTEM,
        tools: list[Any] | None = None,
        max_tokens: int = 8000,
        max_rounds: int | None = 30,
        on_before_round: Callable[[list[dict[str, Any]]], None] | None = None,
        on_stream_token: Callable[[str, Any, list[dict[str, Any]], Any], None] | None = None,
        on_stream_text: Callable[[str, Any, list[dict[str, Any]], Any], None] | None = None,
        on_tool_call: Callable[[str, dict[str, Any], list[dict[str, Any]]], None] | None = None,
        on_tool_result: Callable[[Any, str, list[dict[str, Any]], list[dict[str, Any]]], None] | None = None,
        on_round_end: Callable[[list[dict[str, Any]], list[dict[str, Any]], Any], None] | None = None,
        on_after_round: Callable[[list[dict[str, Any]], Any], None] | None = None,
        on_stop: Callable[[list[dict[str, Any]], Any], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ):
        self._rounds_since_todo = 0
        self._used_todo = False
        # 组合用户自定义回调与内部回调以实现增强功能
        self._user_on_tool_result = on_tool_result
        self._user_on_round_end = on_round_end

        super().__init__(
            client=client,
            model=model,
            system=system,
            tools=list(tools or TOOLS),
            max_tokens=max_tokens,
            max_rounds=max_rounds,
            on_before_round=on_before_round,
            on_stream_token=on_stream_token,
            on_stream_text=on_stream_text,
            on_tool_call=on_tool_call,
            on_tool_result=self._on_tool_result,
            on_round_end=self._on_round_end,
            on_after_round=on_after_round,
            on_stop=on_stop,
            should_stop=should_stop,
        )

    def _on_tool_result(
        self,
        block: Any,
        output: str,
        results: list[dict[str, Any]],
        messages: list[dict[str, Any]],
    ):
        if getattr(block, "name", "") == "todo":
            self._used_todo = True

        if self._user_on_tool_result:
            self._user_on_tool_result(block, output, results, messages)

    def _on_round_end(
        self,
        results: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        response: Any,
    ):
        if self._used_todo:
            self._rounds_since_todo = 0
        else:
            self._rounds_since_todo += 1

        # s03-style reminder injection for long multi-step runs.
        if self._rounds_since_todo >= 3:
            results.insert(
                0,
                {
                    "type": "text",
                    "text": "<reminder>Update your todos.</reminder>",
                },
            )

        self._used_todo = False

        if self._user_on_round_end:
            self._user_on_round_end(results, messages, response)


def build_sql_agent_loop(
    *,
    client: Any,
    model: str,
    **kwargs: Any,
) -> SQLAgentLoop:
    return SQLAgentLoop(client=client, model=model, **kwargs)


__all__ = ["SYSTEM", "TOOLS", "SQLAgentLoop", "build_sql_agent_loop"]


def _try_parse_json(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        return raw
