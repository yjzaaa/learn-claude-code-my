#!/usr/bin/env python3
"""
s03_todo_write.py - 任务清单写入

模型通过 TodoManager 跟踪自己的进度；当它忘记更新时，
提醒机制会强制它补充状态。

    +----------+      +-------+      +---------+
    |   User   | ---> |  LLM  | ---> | Tools   |
    |  prompt  |      |       |      | + todo  |
    +----------+      +---+---+      +----+----+
                          ^               |
                          |   tool_result |
                          +---------------+
                                |
                    +-----------+-----------+
                    | TodoManager state     |
                    | [ ] task A            |
                    | [>] task B <- doing   |
                    | [x] task C            |
                    +-----------------------+
                                |
                    if rounds_since_todo >= 3:
                      inject <reminder>

关键点："代理可以自我跟踪进度，而且这个进度对我可见。"
"""

import os
from pathlib import Path

from client import get_client, get_model
from dotenv import load_dotenv
try:
    from base import BaseAgentLoop, WorkspaceOps, tool
except ImportError:
    from agents.base import BaseAgentLoop, WorkspaceOps, tool

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = get_client()
MODEL = get_model()
OPS = WorkspaceOps(workdir=WORKDIR)

SYSTEM = f"""You are a coding agent at {WORKDIR}.
Use the todo tool to plan multi-step tasks. Mark in_progress before starting, completed when done.
Prefer tools over prose."""


# -- TodoManager：由 LLM 写入的结构化状态 --
class TodoManager:
    def __init__(self):
        self.items = []

    def update(self, items: list) -> str:
        if len(items) > 20:
            raise ValueError("Max 20 todos allowed")
        validated = []
        in_progress_count = 0
        for i, item in enumerate(items):
            text = str(item.get("text", "")).strip()
            status = str(item.get("status", "pending")).lower()
            item_id = str(item.get("id", str(i + 1)))
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
        lines = []
        for item in self.items:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[item["status"]]
            lines.append(f"{marker} #{item['id']}: {item['text']}")
        done = sum(1 for t in self.items if t["status"] == "completed")
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines)


TODO = TodoManager()


@tool(name="todo", description="Update task list. Track progress on multi-step tasks.")
def todo(items: list) -> str:
    return TODO.update(items)


TOOLS = OPS.get_tools() + [todo]

_LOOP_STATE = {"rounds_since_todo": 0, "used_todo": False}


def _on_tool_result(block, output: str, results: list, messages: list):
    print(f"> {block.name}: {output[:200]}")
    if block.name == "todo":
        _LOOP_STATE["used_todo"] = True


def _on_round_end(results: list, messages: list, response):
    if _LOOP_STATE["used_todo"]:
        _LOOP_STATE["rounds_since_todo"] = 0
    else:
        _LOOP_STATE["rounds_since_todo"] += 1

    if _LOOP_STATE["rounds_since_todo"] >= 3:
        results.insert(0, {"type": "text", "text": "<reminder>Update your todos.</reminder>"})

    _LOOP_STATE["used_todo"] = False


AGENT_LOOP = BaseAgentLoop(
    client=client,
    model=MODEL,
    system=SYSTEM,
    tools=TOOLS,
    max_tokens=8000,
    on_tool_result=_on_tool_result,
    on_round_end=_on_round_end,
)


def agent_loop(messages: list):
    AGENT_LOOP.run(messages)


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms03 >> \033[0m")
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
                    print(block.text)
        print()


