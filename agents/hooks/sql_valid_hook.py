"""SQL workflow validation hook.

Validate tool_calls in messages to ensure SQL tasks include at least two steps:
1) schema exploration query
2) final data query
"""

from __future__ import annotations

import json
import re
from typing import Any

try:
    from ..base.abstract import FullAgentHooks
except ImportError:
    from agents.base.abstract import FullAgentHooks


class SqlValidHook(FullAgentHooks):
    """Validate SQL query workflow from tool_calls recorded in messages."""

    SCHEMA_PATTERNS = [
        r"\binformation_schema\b",
        r"\bsys\.(tables|columns|objects|schemas)\b",
        r"\bpg_catalog\b",
        r"\bsqlite_master\b",
        r"\bpragma\s+table_info\b",
        r"\b(show\s+tables|describe\s+\w+)\b",
    ]

    def __init__(self, dialog_id: str):
        self.dialog_id = dialog_id
        self._is_sql_workflow_valid = True
        self._reason = ""
        self._sql_steps: list[str] = []

    def on_before_run(self, messages: list[dict[str, Any]]) -> None:
        _ = messages
        self._is_sql_workflow_valid = True
        self._reason = ""
        self._sql_steps = []

    def on_stream_token(self, chunk: Any) -> None:
        _ = chunk

    def on_tool_call(
        self, name: str, arguments: dict[str, Any], tool_call_id: str = ""
    ) -> None:
        _ = name
        _ = arguments
        _ = tool_call_id

    def on_tool_result(
        self,
        name: str,
        result: str,
        assistant_message: dict[str, Any] | None = None,
        tool_call_id: str = "",
    ) -> None:
        _ = name
        _ = result
        _ = assistant_message
        _ = tool_call_id

    def on_complete(self, content: str) -> None:
        _ = content

    def on_error(self, error: Exception) -> None:
        _ = error

    def on_after_run(self, messages: list[dict[str, Any]], rounds: int) -> None:
        _ = rounds
        sql_calls = self._collect_sql_calls(messages)
        self._sql_steps = sql_calls

        # Only enforce when this round has SQL tool activity.
        if not sql_calls:
            self._is_sql_workflow_valid = True
            self._reason = ""
            return

        has_schema = any(self._is_schema_query(sql) for sql in sql_calls)
        has_data = any(self._is_data_query(sql) for sql in sql_calls)
        has_two_steps = len(sql_calls) >= 2

        self._is_sql_workflow_valid = bool(has_schema and has_data and has_two_steps)
        if self._is_sql_workflow_valid:
            self._reason = ""
            return

        self._reason = (
            "SQL workflow invalid: require at least 2 SQL steps including "
            "schema exploration and final data query."
        )

    def on_stop(self) -> None:
        pass

    def is_sql_workflow_valid(self) -> bool:
        return self._is_sql_workflow_valid

    def get_reason(self) -> str:
        return self._reason

    def get_steps(self) -> list[str]:
        return list(self._sql_steps)

    def _collect_sql_calls(self, messages: list[dict[str, Any]]) -> list[str]:
        calls: list[str] = []
        for msg in messages:
            if msg.get("role") != "assistant":
                continue
            tool_calls = msg.get("tool_calls")
            if not isinstance(tool_calls, list):
                continue
            for tool_call in tool_calls:
                sql = self._extract_sql_from_tool_call(tool_call)
                if sql:
                    calls.append(sql.strip())
        return calls

    def _extract_sql_from_tool_call(self, tool_call: dict[str, Any]) -> str | None:
        if not isinstance(tool_call, dict):
            return None
        fn = tool_call.get("function")
        if not isinstance(fn, dict):
            return None

        name = str(fn.get("name", "")).lower()
        arguments = fn.get("arguments", {})

        parsed_args: dict[str, Any] = {}
        if isinstance(arguments, str):
            try:
                obj = json.loads(arguments)
                if isinstance(obj, dict):
                    parsed_args = obj
            except Exception:
                parsed_args = {"raw": arguments}
        elif isinstance(arguments, dict):
            parsed_args = arguments

        for key in ("sql", "query", "statement"):
            val = parsed_args.get(key)
            if isinstance(val, str) and self._looks_like_sql(val):
                return val

        cmd_val = parsed_args.get("command") or parsed_args.get("cmd") or parsed_args.get("raw")
        if isinstance(cmd_val, str):
            cmd_l = cmd_val.lower()
            if "sql_query.py" in cmd_l or name.startswith("sql"):
                # Fallback: extract first SELECT/WITH block from command text.
                m = re.search(r"((?:select|with)[\s\S]{20,})", cmd_val, flags=re.IGNORECASE)
                if m:
                    return m.group(1)

        return None

    def _looks_like_sql(self, text: str) -> bool:
        return bool(re.search(r"^\s*(select|with)\b", text, flags=re.IGNORECASE))

    def _is_schema_query(self, sql: str) -> bool:
        return any(re.search(p, sql, flags=re.IGNORECASE) for p in self.SCHEMA_PATTERNS)

    def _is_data_query(self, sql: str) -> bool:
        if not self._looks_like_sql(sql):
            return False
        if self._is_schema_query(sql):
            return False
        return bool(re.search(r"\bfrom\b", sql, flags=re.IGNORECASE))
