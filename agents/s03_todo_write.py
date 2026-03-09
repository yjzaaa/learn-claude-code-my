from tkinter import BOTH

from loguru import logger

from agents.prompts import with_base_prompt
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

from dotenv import load_dotenv
try:
    from agents.providers import create_provider_from_env
except ImportError:
    from providers import create_provider_from_env
try:
    from base import BaseAgentLoop, WorkspaceOps, tool
    from agents.s05_skill_loading  import SYSTEM as SKILL_SYSTEM, load_skill, load_skill_reference, load_skill_script
except ImportError:
    from .s05_skill_loading  import SYSTEM as SKILL_SYSTEM, load_skill, load_skill_reference, load_skill_script
    from agents.base import BaseAgentLoop, WorkspaceOps, tool
from .base import build_tools_and_handlers
load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
provider = create_provider_from_env()
MODEL = provider.default_model if provider else "deepseek-chat"
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

SKILL_SYSTEM =  with_base_prompt(SKILL_SYSTEM)

TODO_SYSTEM = with_base_prompt(SYSTEM)

BOTH_SYSTEM = f"{SKILL_SYSTEM}\n\n{TODO_SYSTEM}"
TODO = TodoManager()


class TodoAgent(BaseAgentLoop):
    """
    带任务清单功能的 Agent

    使用 PluginEnabledAgent 作为基类，自动获得技能和上下文压缩支持。
    """

    def __init__(self, **kwargs):
        # 初始化 TodoManager
        self.todo_manager = TodoManager()
        self._loop_state = {"rounds_since_todo": 0, "used_todo": False}

        # 构建工具
        tools, handlers = self._build_toolkit()
        skill_tools, skill_handlers = build_tools_and_handlers([load_skill, load_skill_reference, load_skill_script])
        # 包装工具处理器以追踪 todo 使用
        wrapped_handlers = self._wrap_handlers(skill_handlers | handlers)
        # 初始化 PluginEnabledAgent
        super().__init__(
            system=BOTH_SYSTEM,
            tools=skill_tools + tools,
            tool_handlers=wrapped_handlers   ,
            max_tokens=8000,
            **kwargs
        )

    def _build_toolkit(self) -> tuple[list, dict]:
        """构建工具集"""
        

        @tool(name="todo", description="Update task list. Track progress on multi-step tasks.")
        def todo(items: list) -> str:
            return self.todo_manager.update(items)

        tools, handlers = build_tools_and_handlers(OPS.get_tools() + [todo])
        return tools, handlers

    def _wrap_handlers(self, handlers: dict) -> dict:
        """包装工具处理器以追踪 todo 使用"""
        wrapped = {}
        for name, handler in handlers.items():
            if name == "todo":
                def make_todo_wrapper(h):
                    def todo_wrapper(**kwargs):
                        result = h(**kwargs)
                        self._loop_state["used_todo"] = True
                        return result
                    return todo_wrapper
                wrapped[name] = make_todo_wrapper(handler)
            else:
                wrapped[name] = handler
        return wrapped

    def run_with_inbox(self, messages: list[dict]) -> str:
        """运行 Agent 处理消息"""
        # 重置状态
        self._loop_state["used_todo"] = False

        # 运行（父类会自动调用插件钩子）
        result = self.run(messages)

        # 更新轮次计数（用于提醒机制）
        if self._loop_state["used_todo"]:
            self._loop_state["rounds_since_todo"] = 0
        else:
            self._loop_state["rounds_since_todo"] += 1

        return result


# 向后兼容的全局实例
AGENT_LOOP = TodoAgent()


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
                    logger.info(block.text)
        logger.info("")
