from loguru import logger
#!/usr/bin/env python3
"""
s02_tool_use.py - 工具调用

s01 的代理循环本身没有变化，只是把工具加入 tools 数组，
并新增了一个分发映射来路由调用。

    +----------+      +-------+      +------------------+
    |   User   | ---> |  LLM  | ---> | Tool Dispatch    |
    |  prompt  |      |       |      | {                |
    +----------+      +---+---+      |   bash: run_bash |
                          ^          |   read: run_read |
                          |          |   write: run_wr  |
                          +----------+   edit: run_edit |
                          tool_result| }                |
                                     +------------------+

关键点："循环完全没变，只是加了工具。"
"""

import os
from pathlib import Path

from client import get_client, get_model
from dotenv import load_dotenv
try:
    from base import BaseAgentLoop, WorkspaceOps
except ImportError:
    from agents.base import BaseAgentLoop, WorkspaceOps

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = get_client()
MODEL = get_model()
OPS = WorkspaceOps(workdir=WORKDIR)

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks. Act, don't explain."

# 使用 WorkspaceOps 对外暴露的默认工具列表（bash/read_file/write_file/edit_file）
TOOLS = OPS.get_tools()

AGENT_LOOP = BaseAgentLoop(
    client=client,
    model=MODEL,
    system=SYSTEM,
    tools=TOOLS,
    max_tokens=8000,
)


def agent_loop(messages: list):
    AGENT_LOOP.run(messages)


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms02 >> \033[0m")
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
