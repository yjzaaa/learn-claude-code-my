from loguru import logger
#!/usr/bin/env python3
"""
s07_task_system.py - 任务系统

任务以 JSON 文件形式持久化到 .tasks/，可跨上下文压缩保留。
每个任务包含依赖图关系（blockedBy/blocks）。

    .tasks/
      task_1.json  {"id":1, "subject":"...", "status":"completed", ...}
      task_2.json  {"id":2, "blockedBy":[1], "status":"pending", ...}
      task_3.json  {"id":3, "blockedBy":[2], "blocks":[], ...}

    依赖关系示意：
    +----------+     +----------+     +----------+
    | task 1   | --> | task 2   | --> | task 3   |
    | 已完成   |     | 被阻塞   |     | 被阻塞   |
    +----------+     +----------+     +----------+
         |                ^
         +--- task 1 完成后会从 task 2 的 blockedBy 中移除

关键点："把状态放在对话外部存储，压缩上下文后也不会丢失。"
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
try:
    from agents.providers import create_provider_from_env
    from base import BaseAgentLoop, WorkspaceOps, tool
except ImportError:
    from providers import create_provider_from_env
    from agents.base import BaseAgentLoop, WorkspaceOps, tool

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
provider = create_provider_from_env()
MODEL = provider.default_model if provider else "deepseek-chat"
TASKS_DIR = WORKDIR / ".tasks"
OPS = WorkspaceOps(workdir=WORKDIR)

SYSTEM = f"You are a coding agent at {WORKDIR}. Use task tools to plan and track work."


# -- 任务管理：带依赖图的 CRUD，并持久化为 JSON 文件 --
class TaskManager:
    def __init__(self, tasks_dir: Path):
        self.dir = tasks_dir
        self.dir.mkdir(exist_ok=True)
        self._next_id = self._max_id() + 1

    def _max_id(self) -> int:
        ids = [int(f.stem.split("_")[1]) for f in self.dir.glob("task_*.json")]
        return max(ids) if ids else 0

    def _load(self, task_id: int) -> dict:
        path = self.dir / f"task_{task_id}.json"
        if not path.exists():
            raise ValueError(f"Task {task_id} not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, task: dict):
        path = self.dir / f"task_{task['id']}.json"
        path.write_text(json.dumps(task, indent=2), encoding="utf-8")

    def create(self, subject: str, description: str = "") -> str:
        task = {
            "id": self._next_id, "subject": subject, "description": description,
            "status": "pending", "blockedBy": [], "blocks": [], "owner": "",
        }
        self._save(task)
        self._next_id += 1
        return json.dumps(task, indent=2)

    def get(self, task_id: int) -> str:
        return json.dumps(self._load(task_id), indent=2)

    def update(self, task_id: int, status: str = None,
               add_blocked_by: list = None, add_blocks: list = None) -> str:
        task = self._load(task_id)
        if status:
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Invalid status: {status}")
            task["status"] = status
            # 任务完成后，从其他任务的 blockedBy 中移除该任务
            if status == "completed":
                self._clear_dependency(task_id)
        if add_blocked_by:
            task["blockedBy"] = list(set(task["blockedBy"] + add_blocked_by))
        if add_blocks:
            task["blocks"] = list(set(task["blocks"] + add_blocks))
            # 双向维护：同时更新被阻塞任务的 blockedBy 列表
            for blocked_id in add_blocks:
                try:
                    blocked = self._load(blocked_id)
                    if task_id not in blocked["blockedBy"]:
                        blocked["blockedBy"].append(task_id)
                        self._save(blocked)
                except ValueError:
                    pass
        self._save(task)
        return json.dumps(task, indent=2)

    def _clear_dependency(self, completed_id: int):
        """将 completed_id 从所有任务的 blockedBy 列表中移除。"""
        for f in self.dir.glob("task_*.json"):
            task = json.loads(f.read_text(encoding="utf-8"))
            if completed_id in task.get("blockedBy", []):
                task["blockedBy"].remove(completed_id)
                self._save(task)

    def list_all(self) -> str:
        tasks = []
        for f in sorted(self.dir.glob("task_*.json")):
            tasks.append(json.loads(f.read_text(encoding="utf-8")))
        if not tasks:
            return "No tasks."
        lines = []
        for t in tasks:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}.get(t["status"], "[?]")
            blocked = f" (blocked by: {t['blockedBy']})" if t.get("blockedBy") else ""
            lines.append(f"{marker} #{t['id']}: {t['subject']}{blocked}")
        return "\n".join(lines)


TASKS = TaskManager(TASKS_DIR)


@tool(name="task_create", description="Create a new task.")
def task_create(subject: str, description: str = "") -> str:
    return TASKS.create(subject, description)


@tool(name="task_update", description="Update a task's status or dependencies.")
def task_update(
    task_id: int,
    status: str | None = None,
    addBlockedBy: list[int] | None = None,
    addBlocks: list[int] | None = None,
) -> str:
    return TASKS.update(task_id, status, addBlockedBy, addBlocks)


@tool(name="task_list", description="List all tasks with status summary.")
def task_list() -> str:
    return TASKS.list_all()


@tool(name="task_get", description="Get full details of a task by ID.")
def task_get(task_id: int) -> str:
    return TASKS.get(task_id)


TOOLS = OPS.get_tools() + [task_create, task_update, task_list, task_get]


def _on_tool_result(block, output: str, results: list, messages: list):
    logger.info(f"> {block.name}: {str(output)[:200]}")
AGENT_LOOP = BaseAgentLoop(
    provider=provider,
    model=MODEL,
    system=SYSTEM,
    tools=TOOLS,
    max_tokens=8000,
    on_tool_result=_on_tool_result,
)


def agent_loop(messages: list):
    AGENT_LOOP.run(messages)


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms07 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    logger.info(block.text)
        logger.info("")
