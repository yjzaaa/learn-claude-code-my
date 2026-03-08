"""
s_full_refactored.py - 使用 BaseInteractiveAgent 重构的 Full Agent

保留了 s_full.py 的所有功能，但使用 BaseInteractiveAgent 架构：
- 自动消息生命周期管理
- 内置流式输出
- 前端实时同步
- 复用 WorkspaceOps 基础工具
"""

import os
import uuid
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

# 基础架构导入
try:
    from .base import StreamingAgent, tool, WorkspaceOps, build_tools_and_handlers
except ImportError:
    from agents.base import StreamingAgent, tool, WorkspaceOps, build_tools_and_handlers

try:
    from .s05_skill_loading import SkillLoader
except ImportError:
    from agents.s05_skill_loading import SkillLoader

try:
    from .s07_task_system import TaskManager
except ImportError:
    from agents.s07_task_system import TaskManager

try:
    from .client import get_client, get_model
except ImportError:
    from agents.client import get_client, get_model

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = get_client()
MODEL = get_model()

SKILLS_DIR = WORKDIR / "skills"
TASKS_DIR = WORKDIR / ".tasks"


# ============================================================================
# TodoManager - 任务列表管理
# ============================================================================

class TodoManager:
    """任务列表管理 (s03)"""

    def __init__(self):
        self.items = []

    def update(self, items: list) -> str:
        validated, ip = [], 0
        for i, item in enumerate(items):
            content = str(item.get("content", "")).strip()
            status = str(item.get("status", "pending")).lower()
            af = str(item.get("activeForm", "")).strip()
            if not content:
                raise ValueError(f"Item {i}: content required")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Item {i}: invalid status '{status}'")
            if not af:
                raise ValueError(f"Item {i}: activeForm required")
            if status == "in_progress":
                ip += 1
            validated.append({"content": content, "status": status, "activeForm": af})
        if len(validated) > 20:
            raise ValueError("Max 20 todos")
        if ip > 1:
            raise ValueError("Only one in_progress allowed")
        self.items = validated
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "No todos."
        lines = []
        for item in self.items:
            m = {"completed": "[x]", "in_progress": "[>]", "pending": "[ ]"}.get(
                item["status"], "[?]"
            )
            suffix = f" <- {item['activeForm']}" if item["status"] == "in_progress" else ""
            lines.append(f"{m} {item['content']}{suffix}")
        done = sum(1 for t in self.items if t["status"] == "completed")
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines)

    def has_open_items(self) -> bool:
        return any(item.get("status") != "completed" for item in self.items)


# 全局实例
TODO = TodoManager()
SKILLS = SkillLoader(SKILLS_DIR)
TASK_MGR = TaskManager(TASKS_DIR)


# ============================================================================
# FullAgent 类 - 使用 BaseInteractiveAgent 重构
# ============================================================================

class FullAgent(StreamingAgent):
    """
    Full Agent - 重构后的完整代理 (使用 StreamingAgent)

    特性:
    - 自动消息生命周期管理
    - 流式输出到前端 (通过 Transport 层)
    - 工具调用自动同步
    - 复用 WorkspaceOps 基础工具
    - 支持 LangChain 消息类型
    """

    def __init__(self, dialog_id: str):
        self.workdir = WORKDIR
        self.workspace = WorkspaceOps(workdir=WORKDIR)

        # 构建系统提示
        system = f"""You are a coding agent at {WORKDIR}.
Use tools to solve tasks.
Prefer task_create/task_update/task_list for multi-step work.
Use TodoWrite for short checklists.

Available skills:
{SKILLS.get_descriptions()}"""

        # 收集所有工具函数（返回 tools 和 tool_handlers）
        tools, tool_handlers = self._build_tools()

        # 通过反射获取实际类名
        actual_class_name = self.__class__.__name__

        super().__init__(
            client=client,
            model=MODEL,
            system=system,
            tools=tools,
            tool_handlers=tool_handlers,
            dialog_id=dialog_id,
            agent_type=actual_class_name,
            max_tokens=8000,
            max_rounds=25,
            enable_streaming=True,
        )

    def _build_tools(self) -> tuple[list[dict[str, Any]], dict[str, Callable]]:
        """构建工具列表和处理函数：复用 WorkspaceOps 基础工具 + FullAgent 特有工具"""
        # 1. 获取 WorkspaceOps 基础工具（bash, read_file, write_file, edit_file）
        base_tools = list(self.workspace.get_tools(as_dict=False))

        # 2. 定义 FullAgent 特有工具
        @tool(name="TodoWrite", description="Update task tracking list.")
        def todo_write(items: list) -> str:
            """Update task tracking list."""
            try:
                return TODO.update(items)
            except Exception as e:
                return f"Error: {e}"

        @tool(name="task_create", description="Create a persistent file task.")
        def task_create(subject: str, description: str = "") -> str:
            """Create a persistent file task."""
            try:
                return TASK_MGR.create(subject, description)
            except Exception as e:
                return f"Error: {e}"

        @tool(name="task_get", description="Get task details by ID.")
        def task_get(task_id: int) -> str:
            """Get task details by ID."""
            try:
                return TASK_MGR.get(task_id)
            except Exception as e:
                return f"Error: {e}"

        @tool(name="task_update", description="Update task status or dependencies.")
        def task_update(
            task_id: int,
            status: str = None,
            add_blocked_by: list = None,
            add_blocks: list = None,
        ) -> str:
            """Update task status or dependencies."""
            try:
                return TASK_MGR.update(task_id, status, add_blocked_by, add_blocks)
            except Exception as e:
                return f"Error: {e}"

        @tool(name="task_list", description="List all tasks.")
        def task_list() -> str:
            """List all tasks."""
            return TASK_MGR.list_all()

        @tool(name="claim_task", description="Claim a task from the board.")
        def claim_task(task_id: int) -> str:
            """Claim a task from the board."""
            try:
                return TASK_MGR.claim(task_id, "lead")
            except Exception as e:
                return f"Error: {e}"

        @tool(name="load_skill", description="Load specialized knowledge by name.")
        def load_skill(name: str) -> str:
            """Load specialized knowledge by name."""
            return SKILLS.get_content(name)

        # 3. 合并所有工具
        all_tools = base_tools + [
            todo_write, task_create, task_get, task_update,
            task_list, claim_task, load_skill
        ]

        # 4. 转换为 Anthropic 工具格式和 handlers
        return build_tools_and_handlers(all_tools)

    async def run(self, user_input: str) -> None:
        """运行一次对话 (异步)"""
        await super().run(user_input)


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    import sys
    import asyncio

    dialog_id = sys.argv[1] if len(sys.argv) > 1 else str(uuid.uuid4())
    agent = FullAgent(dialog_id)

    print(f"FullAgent started (dialog_id: {dialog_id})")
    print("Type your message or 'q' to quit")

    async def main_loop():
        while True:
            try:
                query = input("\n>> ")
            except (EOFError, KeyboardInterrupt):
                break

            if query.strip().lower() in ("q", "exit", "quit"):
                break

            await agent.run(query)

    asyncio.run(main_loop())
