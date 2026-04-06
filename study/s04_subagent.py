from loguru import logger

#!/usr/bin/env python3
"""
s04_subagent.py - 子代理

创建一个子代理并使用全新的 messages=[]。子代理在独立上下文中工作，
与父代理共享文件系统，但最终只向父代理返回摘要。

    Parent agent                     Subagent
    +------------------+             +------------------+
    | messages=[...]   |             | messages=[]      |  <-- fresh
    |                  |  dispatch   |                  |
    | tool: task       | ---------->| while tool_use:  |
    |   prompt="..."   |            |   call tools     |
    |   description="" |            |   append results |
    |                  |  summary   |                  |
    |   result = "..." | <--------- | return last text |
    +------------------+             +------------------+
              |
    父代理上下文保持干净。
    子代理上下文在结束后丢弃。

关键点："进程隔离天然带来上下文隔离。"
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
except ImportError:
    from agents.base import BaseAgentLoop, WorkspaceOps, tool

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
provider = create_provider_from_env()
MODEL = provider.default_model if provider else "deepseek-chat"
OPS = WorkspaceOps(workdir=WORKDIR)

SYSTEM = f"You are a coding agent at {WORKDIR}. Use the task tool to delegate exploration or subtasks."
SUBAGENT_SYSTEM = f"You are a coding subagent at {WORKDIR}. Complete the given task, then summarize your findings."

# 子代理拥有全部基础工具，但不包含 task（避免递归再派发）
CHILD_TOOLS = OPS.get_tools()


# -- 子代理：独立上下文、受限工具、仅返回摘要 --
CHILD_AGENT_LOOP = BaseAgentLoop(
    provider=provider,
    model=MODEL,
    system=SUBAGENT_SYSTEM,
    tools=CHILD_TOOLS,
    max_tokens=8000,
    max_rounds=30,
)


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


def run_subagent(prompt: str) -> str:
    sub_messages = [{"role": "user", "content": prompt}]  # 全新上下文
    CHILD_AGENT_LOOP.run(sub_messages)

    # 子代理上下文会被丢弃，只向父代理返回最终文本摘要。
    for msg in reversed(sub_messages):
        if msg.get("role") == "assistant":
            summary = _extract_final_text(msg.get("content"))
            return summary or "(no summary)"
    return "(no summary)"


def run_task(prompt: str, description: str | None = None) -> str:
    desc = description or "subtask"
    logger.info(f"> task ({desc}): {prompt[:80]}")
    return run_subagent(prompt)


@tool(
    name="task",
    description="Spawn a subagent with fresh context. It shares the filesystem but not conversation history.",
)
def task(prompt: str, description: str | None = None) -> str:
    return run_task(prompt, description)


# -- 父代理工具：基础工具 + task 分发器 --
PARENT_TOOLS = CHILD_TOOLS + [task]


def _on_tool_result(block, output: str, results: list, messages: list):
    logger.info(f"  {output[:200]}")
AGENT_LOOP = BaseAgentLoop(
    provider=provider,
    model=MODEL,
    system=SYSTEM,
    tools=PARENT_TOOLS,
    max_tokens=8000,
    on_tool_result=_on_tool_result,
)


def agent_loop(messages: list):
    AGENT_LOOP.run(messages)


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms04 >> \033[0m")
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
