from loguru import logger
#!/usr/bin/env python3
"""
s01_agent_loop.py - 代理循环

AI 编码代理的核心秘密，其实就是这一种循环模式：

    while stop_reason == "tool_use":
        response = LLM(messages, tools)
        execute tools
        append results

    +----------+      +-------+      +---------+
    |   User   | ---> |  LLM  | ---> |  Tool   |
    |  prompt  |      |       |      | execute |
    +----------+      +---+---+      +----+----+
                          ^               |
                          |   tool_result |
                          +---------------+
                          (loop continues)

这就是核心循环：持续把工具结果回填给模型，
直到模型决定停止。生产级代理通常会在其上
叠加策略、回调和生命周期控制。
"""

import os
from pathlib import Path

from dotenv import load_dotenv
try:
    from client import get_client, get_model
except ImportError:
    from agents.client import get_client, get_model
try:
    from base import BaseAgentLoop, WorkspaceOps
except ImportError:
    from agents.base import BaseAgentLoop, WorkspaceOps

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

client = get_client()
MODEL = get_model()
# 没有目录就创建一个，避免工具调用失败
workpath = Path.cwd() / ".workspace"
workpath.mkdir(exist_ok=True)
OPS = WorkspaceOps(workdir=workpath)

SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

# 注册工具列表和循环实例（此处只启用 bash）
bash_tool = OPS.get_tools(as_dict=True)["bash"]
TOOLS = [bash_tool]

AGENT_LOOP = BaseAgentLoop(
    client=client,
    model=MODEL,
    system=SYSTEM,
    tools=TOOLS,
    max_tokens=8000,
)


def agent_loop(messages: list):
    """复用 base 中的通用循环实现。"""
    AGENT_LOOP.run(messages)


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
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
