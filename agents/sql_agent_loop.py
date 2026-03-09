"""Composed SQL agent loop: s05 skills + s03 todo behavior + s06 context compact + s04 task."""

from __future__ import annotations

import json
import os
import re
import time
import weakref
from pathlib import Path
from typing import Any, Callable

from loguru import logger

# -- s06 上下文压缩配置 --
_COMPACT_THRESHOLD = int(os.getenv("AGENT_COMPACT_THRESHOLD", "50000"))  # token阈值，超过则自动压缩
_COMPACT_KEEP_RECENT = 3  # micro_compact保留的最近tool_result数量
_TRANSCRIPT_DIR = Path(os.getenv("AGENT_TRANSCRIPT_DIR", ".transcripts"))  # 完整对话保存目录

try:
    from .base import BaseAgentLoop, tool
    from .s05_skill_loading import SYSTEM as S05_SYSTEM, TOOLS as S05_TOOLS
except ImportError:
    from agents.base import BaseAgentLoop, tool
    from agents.s05_skill_loading import SYSTEM as S05_SYSTEM, TOOLS as S05_TOOLS

_TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FORBIDDEN_SQL = ("drop ", "truncate ", "alter ", "create ", "exec ", "xp_")


class TodoManager:
    """内存中的待办事项跟踪器，改编自 s03_todo_write。

    架构图: Todo 在 Agent Loop 中的运行方式
    =========================================

        +-------------------+         +------------------+
        |   用户输入         |-------->|   Agent 循环     |
        +-------------------+         | (SQLAgentLoop)   |
                                      +--------+---------+
                                               |
                                               v
        +-------------------+         +------------------+
        |   TodoManager     |<--------|   todo 工具      |
        |   (状态存储)       |         | (update/render)  |
        +--------+---------+         +--------+---------+
                 |                            |
                 |    +------------------+    |
                 |    |  日志记录 todo   |<---+
                 |    |    状态变化      |
                 |    +------------------+
                 |
                 v
        +-------------------+
        |    状态标记:      |
        |  [ ] = 待处理     |
        |  [>] = 进行中     |
        |  [x] = 已完成     |
        +-------------------+
                 |
                 v
        +------------------------+
        |      提醒策略:         |
        |  rounds_since_todo >= 3|
        |  -> 注入提醒           |
        +------------------------+

    工作流程:
    1. Agent 调用 `todo` 工具传入事项列表
    2. TodoManager 验证并更新状态
    3. 日志输出当前状态 (完成数/总数)
    4. 循环跟踪 rounds_since_todo, 超时时提醒
    """

    def __init__(self):
        self.items: list[dict[str, str]] = []
        self._logger = None

    def _get_logger(self):
        if self._logger is None:
            from loguru import logger
            self._logger = logger
        return self._logger

    def update(self, items: list) -> str:
        """更新待办事项列表。

        Args:
            items: LLM传入的待办事项列表，每个item是包含id/text/status的字典。
                   正确格式: [{"id": "1", "text": "查询数据", "status": "completed"}]
                   错误格式: "1. 查询数据" (字符串)

        Returns:
            渲染后的待办事项文本，供LLM查看当前进度。

        Raises:
            ValueError: 当items不是列表、todo数量超过20、缺少text、状态无效或同时有多个进行中任务时。
        """
        # 类型检查：确保items是列表，防止传入字符串导致误判长度
        if not isinstance(items, list):
            raise ValueError(f"items必须是列表(list)，当前类型: {type(items).__name__}。正确格式: [{'{'}'id': '1', 'text': '任务', 'status': 'pending'{'}'}]")

        # 限制todo数量，防止LLM生成过多任务导致管理混乱
        if len(items) > 20:
            raise ValueError("Max 20 todos allowed")

        validated: list[dict[str, str]] = []
        in_progress_count = 0  # 统计"进行中"状态的任务数

        # 遍历并验证每个待办事项
        for idx, item in enumerate(items):
            # 提取字段：id默认使用索引+1，status默认pending
            item_id = str(item.get("id", str(idx + 1))).strip()
            text = str(item.get("text", "")).strip()
            status = str(item.get("status", "pending")).lower().strip()

            # 验证规则1：任务描述不能为空
            if not text:
                raise ValueError(f"Item {item_id}: text required")

            # 验证规则2：状态必须是允许的值
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Item {item_id}: invalid status '{status}'")

            # 统计进行中任务数量（后面检查是否超过1个）
            if status == "in_progress":
                in_progress_count += 1

            validated.append({"id": item_id, "text": text, "status": status})

        # 验证规则3：同时只能有一个任务在进行中（聚焦单一任务）
        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress at a time")

        # 保存验证后的数据
        self.items = validated
        result = self.render()

        # 打印详细日志：总体进度 + 每个任务的完成状态
        done_count = sum(1 for item in validated if item["status"] == "completed")
        self._get_logger().info(f"[todo_update] {done_count}/{len(self.items)} completed, in_progress: {in_progress_count}")
        for item in validated:
            icon = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[item["status"]]
            self._get_logger().info(f"  {icon} #{item['id']}: {item['text']}")

        return result

    def render(self) -> str:
        if not self.items:
            return "No todos."

        marker_map = {
            "pending": "[ ]",
            "in_progress": "[>]",
            "completed": "[x]",
        }
        from loguru import logger
        logger.info(f"[todo_render] items={self.items}")
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


@tool(name="compact", description="Trigger manual conversation compression to reduce context length.")
def compact(focus: str | None = None) -> str:
    """第3层压缩：由模型手动触发。

    Args:
        focus: 可选的关注点提示，告诉压缩应该重点关注什么。

    Returns:
        压缩触发确认，实际压缩在 after_round 中执行。
    """
    return f"Compacting... (focus: {focus or 'general'})"


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

COMPACT_WORKFLOW_CONSTRAINT = """
[Context compact policy]
- When context grows too long (token limit approaching), use the `compact` tool to compress conversation history.
- The compact tool preserves essential information while removing redundant details.
- After compact, you receive a summary of the conversation and the full transcript is saved to disk.
""".strip()

TASK_WORKFLOW_CONSTRAINT = """
[Task delegation policy]
- For complex multi-part analysis, use the `task` tool to delegate subtasks to a subagent.
- The subagent has fresh context and can work independently without cluttering the main conversation.
- Provide clear, specific prompts when delegating tasks.
- Use task delegation for: schema exploration, data validation, complex calculations, or independent analysis branches.
""".strip()

SYSTEM = (
    f"{S05_SYSTEM}\n\n"
    # f"{SQL_WORKFLOW_CONSTRAINT}\n\n"
    f"{TODO_WORKFLOW_CONSTRAINT}\n\n"
    f"{TODO_REMINDER_POLICY}\n\n"
    f"{COMPACT_WORKFLOW_CONSTRAINT}\n\n"
    f"{TASK_WORKFLOW_CONSTRAINT}"
)

# ============================================================================
# s04 Task 工具 - 子代理委派（前置定义以便加入TOOLS）
# ============================================================================

# 用于存储当前活跃的SQLAgentLoop实例的弱引用
_active_loops: weakref.WeakSet = weakref.WeakSet()

# 子代理系统提示词（简化版，专注于SQL/数据分析任务）
_SUBAGENT_SYSTEM = """You are a SQL and data analysis subagent.
Complete the given task using available tools, then summarize your findings concisely.
Focus on: 1) What was queried/analyzed, 2) Key results, 3) Any errors encountered.
Do not use the task tool (no recursive delegation)."""


def _extract_final_text(content) -> str:
    """提取 assistant 最终文本内容。"""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts = []
    for block in content:
        if hasattr(block, "text") and block.text:
            parts.append(str(block.text))
            continue
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            if text:
                parts.append(str(text))
    return "\n".join(parts)


def _create_subagent_loop(provider: Any, model: str) -> BaseAgentLoop:
    """创建子代理循环（不含task工具，避免递归）。"""
    # 子代理拥有基础技能工具，但不包含task
    subagent_tools = list(S05_TOOLS) + [
        todo,
        compact,
    ]
    return BaseAgentLoop(
        provider=provider,
        model=model,
        system=_SUBAGENT_SYSTEM,
        tools=subagent_tools,
        max_tokens=8000,
        max_rounds=20,
    )


def _run_subagent(prompt: str, provider: Any, model: str) -> str:
    """运行子代理并返回摘要。"""
    subagent = _create_subagent_loop(provider, model)
    sub_messages = [{"role": "user", "content": prompt}]  # 全新上下文
    subagent.run(sub_messages)

    # 从后向前查找assistant的回复
    for msg in reversed(sub_messages):
        if msg.get("role") == "assistant":
            summary = _extract_final_text(msg.get("content"))
            return summary or "(no summary)"
    return "(no summary)"


def _run_subagent_with_active_loop(prompt: str, desc: str) -> str:
    """使用当前活跃的loop的provider/model运行子代理。"""
    # 尝试获取活跃的loop
    for loop in _active_loops:
        if hasattr(loop, "_client") and hasattr(loop, "_model"):
            provider = loop._client
            model = loop._model
            result = _run_subagent(prompt, provider, model)
            logger.info(f"< task ({desc}): {result[:200]}...")
            return result

    # 如果没有活跃的loop，使用环境变量配置
    logger.warning("[task] No active SQLAgentLoop found, using fallback provider")
    try:
        from agents.providers import create_provider_from_env
        provider = create_provider_from_env()
        model = provider.default_model if provider else "deepseek-chat"
        result = _run_subagent(prompt, provider, model)
        logger.info(f"< task ({desc}): {result[:200]}...")
        return result
    except ImportError:
        return "[Error] Cannot create subagent: no active loop and providers module not available"


@tool(
    name="task",
    description="Spawn a subagent with fresh context to handle delegated work. It shares the filesystem but not conversation history. Returns a summary when complete.",
)
def task(prompt: str, description: str | None = None) -> str:
    """委派任务给子代理执行。

    Args:
        prompt: 给子代理的完整任务描述
        description: 可选的任务描述/标签，用于日志

    Returns:
        子代理执行结果的摘要
    """
    desc = description or "subtask"
    logger.info(f"> task ({desc}): {prompt[:80]}...")

    # 从SQLAgentLoop实例获取client和model（通过弱引用存储的当前活跃loop）
    return _run_subagent_with_active_loop(prompt, desc)


# 工具列表：基础技能 + 组合功能
def _get_sql_runner():
    """Resolve SQL execution backend used by generic SQL tools."""
    from skills.finance.scripts.sql_query import run_sql_query
    return run_sql_query


TOOLS = list(S05_TOOLS) + [
    todo,
    compact,
    task,
    # sql_execute,
    # sql_validate,
    # sql_describe_table,
]


class SQLAgentLoop(BaseAgentLoop):
    """Composable agent loop that merges s05, s03, s04 and s06 behaviors.

    功能集成:
    - s05: Skill加载和执行
    - s03: Todo任务管理
    - s04: Task子代理委派 (用新鲜上下文处理独立子任务)
    - s06: 三层上下文压缩 (micro_compact, auto_compact, compact工具)
    """

    def __init__(
        self,
        *,
        provider: Any,
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
        # s06 压缩配置
        compact_threshold: int = _COMPACT_THRESHOLD,
        compact_keep_recent: int = _COMPACT_KEEP_RECENT,
        enable_compact: bool = True,
    ):
        # s03: Todo追踪状态
        self._rounds_since_todo = 0
        self._used_todo = False

        # s06: 压缩状态
        self._enable_compact = enable_compact
        self._compact_threshold = compact_threshold
        self._compact_keep_recent = compact_keep_recent
        self._compact_requested = False  # 标记是否收到compact工具调用

        # 保存引用供压缩使用
        self._client = provider
        self._model = model

        # 组合用户自定义回调与内部回调以实现增强功能
        self._user_on_tool_result = on_tool_result
        self._user_on_round_end = on_round_end
        self._user_on_before_round = on_before_round
        self._user_on_after_round = on_after_round

        super().__init__(
            provider=provider,
            model=model,
            system=system,
            tools=list(tools or TOOLS),
            max_tokens=max_tokens,
            max_rounds=max_rounds,
        )

    def _on_before_round(self, messages: list[dict[str, Any]]):
        """每轮开始前执行：s06 第1层和第2层压缩。"""
        # 先调用用户的回调（如果存在）
        if self._user_on_before_round:
            self._user_on_before_round(messages)

        if not self._enable_compact:
            return

        # s06 第1层：每轮静默微压缩（清理旧tool_result）
        _micro_compact(messages, keep_recent=self._compact_keep_recent)

        # s06 第2层：token超阈值时自动压缩
        current_tokens = _estimate_tokens(messages)
        if current_tokens > self._compact_threshold:
            logger.info(f"[auto_compact] token数 {current_tokens} 超过阈值 {self._compact_threshold}，触发自动压缩")
            messages[:] = _auto_compact(messages, client=self._client, model=self._model)

    def _on_tool_result(
        self,
        block: Any,
        output: str,
        results: list[dict[str, Any]],
        messages: list[dict[str, Any]],
    ):
        # s03: 追踪todo工具使用
        if getattr(block, "name", "") == "todo":
            self._used_todo = True

        # s06: 检测compact工具调用（第3层压缩 - 手动触发）
        if getattr(block, "name", "") == "compact":
            self._compact_requested = True

        if self._user_on_tool_result:
            self._user_on_tool_result(block, output, results, messages)

    def _on_round_end(
        self,
        results: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        response: Any,
    ):
        # s03: 追踪todo更新状态
        if self._used_todo:
            self._rounds_since_todo = 0
        else:
            self._rounds_since_todo += 1

        # s03: 长时间未更新todo时注入提醒
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

    def _on_after_round(self, messages: list[dict[str, Any]], response: Any):
        """每轮结束后执行：s06 第3层手动压缩。"""
        # s06 第3层：如果本轮调用了compact工具，执行手动压缩
        if self._enable_compact and self._compact_requested:
            logger.info("[manual_compact] 执行手动上下文压缩")
            messages[:] = _auto_compact(messages, client=self._client, model=self._model)
            self._compact_requested = False

        # 最后调用用户的回调（如果存在）
        if self._user_on_after_round:
            self._user_on_after_round(messages, response)

    def run(self, messages: list[dict[str, Any]]) -> Any:
        """运行agent循环，注册自身到活跃集合供task工具使用。"""
        _active_loops.add(self)
        try:
            return super().run(messages)
        finally:
            _active_loops.discard(self)


def build_sql_agent_loop(
    *,
    provider: Any,
    model: str,
    **kwargs: Any,
) -> SQLAgentLoop:
    return SQLAgentLoop(provider=provider, model=model, **kwargs)


__all__ = ["SYSTEM", "TOOLS", "SQLAgentLoop", "build_sql_agent_loop"]


def _try_parse_json(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        return raw


# ============================================================================
# s06 上下文压缩机制 - 三层流水线
# ============================================================================

def _estimate_tokens(messages: list) -> int:
    """粗略估算token数：约4个字符约等于1个token。"""
    return len(str(messages)) // 4


def _micro_compact(messages: list, keep_recent: int = _COMPACT_KEEP_RECENT) -> list:
    """第1层压缩：每轮静默执行，将旧tool_result替换为占位符。

    将除最近 keep_recent 条以外的 tool_result 内容替换为 "[Previous: used {tool_name}]"
    这是最小侵入性的压缩，不会丢失信息，只是简化旧工具结果的显示。
    """
    # 收集所有 tool_result 的位置与内容
    tool_results = []
    for msg_idx, msg in enumerate(messages):
        if msg["role"] == "user" and isinstance(msg.get("content"), list):
            for part_idx, part in enumerate(msg["content"]):
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    tool_results.append((msg_idx, part_idx, part))

    if len(tool_results) <= keep_recent:
        return messages

    # 通过 tool_use_id 回溯对应的工具名
    tool_name_map = {}
    for msg in messages:
        if msg["role"] == "assistant":
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if hasattr(block, "type") and block.type == "tool_use":
                        tool_name_map[block.id] = block.name

    # 清理旧结果（仅保留最近 keep_recent 条完整内容）
    to_clear = tool_results[:-keep_recent]
    cleared_count = 0
    for _, _, result in to_clear:
        if isinstance(result.get("content"), str) and len(result["content"]) > 100:
            tool_id = result.get("tool_use_id", "")
            tool_name = tool_name_map.get(tool_id, "unknown")
            result["content"] = f"[Previous: used {tool_name}]"
            cleared_count += 1

    if cleared_count > 0:
        logger.debug(f"[micro_compact] 清理了 {cleared_count} 条旧tool_result")
    return messages


def _auto_compact(messages: list, client: Any, model: str) -> list:
    """第2层压缩：token超阈值时自动压缩。

    1. 保存完整对话到 .transcripts/
    2. 请求LLM生成会话摘要
    3. 用摘要替换当前messages
    """
    # 将完整对话写入磁盘
    _TRANSCRIPT_DIR.mkdir(exist_ok=True)
    transcript_path = _TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str, ensure_ascii=False) + "\n")
    logger.debug(f"[auto_compact] 完整对话已保存: {transcript_path}")

    # 请求模型生成连续性摘要
    conversation_text = json.dumps(messages, default=str, ensure_ascii=False)[:80000]
    try:
        response = client.messages.create(
            model=model,
            messages=[{"role": "user", "content":
                "Summarize this conversation for continuity. Include: "
                "1) What was accomplished, 2) Current state, 3) Key decisions made. "
                "Be concise but preserve critical details.\n\n" + conversation_text}],
            max_tokens=2000,
        )
        summary = response.content[0].text
    except Exception as e:
        logger.warning(f"[auto_compact] 生成摘要失败: {e}")
        summary = "[Conversation summary unavailable due to error]"

    # 用压缩后的摘要替换当前上下文
    return [
        {"role": "user", "content": f"[Conversation compressed. Transcript: {transcript_path}]\n\n{summary}"},
        {"role": "assistant", "content": "Understood. I have the context from the summary. Continuing."},
    ]
