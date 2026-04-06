from loguru import logger

#!/usr/bin/env python3
"""
s08_background_tasks.py - 后台任务

在后台线程执行命令，并在每次模型调用前清空通知队列注入结果。

    主线程                     后台线程
    +-----------------+        +-----------------+
    | agent loop      |        | task executes   |
    | ...             |        | ...             |
    | [LLM call] <---+------- | enqueue(result) |
    | ^清空队列       |        +-----------------+
    +-----------------+

    时间线：
    Agent ----[spawn A]----[spawn B]----[other work]----
                 |              |
                 v              v
              [A runs]      [B runs]        (并行)
                 |              |
                 +-- notification queue --> [注入结果]

关键点："发起即返回，代理不会因长命令阻塞。"
"""

import os
import subprocess
import threading
import uuid
from pathlib import Path

from dotenv import load_dotenv

try:
    from agents.providers import create_provider_from_env
    from base import BaseAgentLoop, WorkspaceOps, tool
except ImportError:
    from agents.base import BaseAgentLoop, WorkspaceOps, tool
    from providers import create_provider_from_env

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
provider = create_provider_from_env()
MODEL = provider.default_model if provider else "deepseek-chat"
OPS = WorkspaceOps(workdir=WORKDIR)

SYSTEM = f"You are a coding agent at {WORKDIR}. Use background_run for long-running commands."


# -- 后台任务管理：线程执行 + 通知队列 --
class BackgroundManager:
    def __init__(self):
        self.tasks = {}  # task_id -> {status, result, command}
        self._notification_queue = []  # completed task results
        self._lock = threading.Lock()

    def run(self, command: str) -> str:
        """启动后台线程并立即返回 task_id。"""
        task_id = str(uuid.uuid4())[:8]
        self.tasks[task_id] = {"status": "running", "result": None, "command": command}
        thread = threading.Thread(
            target=self._execute, args=(task_id, command), daemon=True
        )
        thread.start()
        return f"Background task {task_id} started: {command[:80]}"

    def _execute(self, task_id: str, command: str):
        """线程入口：执行子进程，采集输出并写入通知队列。"""
        try:
            r = subprocess.run(
                command, shell=True, cwd=WORKDIR,
                capture_output=True, text=True, timeout=300
            )
            output = (r.stdout + r.stderr).strip()[:50000]
            status = "completed"
        except subprocess.TimeoutExpired:
            output = "Error: Timeout (300s)"
            status = "timeout"
        except Exception as e:
            output = f"Error: {e}"
            status = "error"
        self.tasks[task_id]["status"] = status
        self.tasks[task_id]["result"] = output or "(no output)"
        with self._lock:
            self._notification_queue.append({
                "task_id": task_id,
                "status": status,
                "command": command[:80],
                "result": (output or "(no output)")[:500],
            })

    def check(self, task_id: str = None) -> str:
        """查询单个任务状态，或列出全部任务。"""
        if task_id:
            t = self.tasks.get(task_id)
            if not t:
                return f"Error: Unknown task {task_id}"
            return f"[{t['status']}] {t['command'][:60]}\n{t.get('result') or '(running)'}"
        lines = []
        for tid, t in self.tasks.items():
            lines.append(f"{tid}: [{t['status']}] {t['command'][:60]}")
        return "\n".join(lines) if lines else "No background tasks."

    def drain_notifications(self) -> list:
        """返回并清空所有待处理完成通知。"""
        with self._lock:
            notifs = list(self._notification_queue)
            self._notification_queue.clear()
        return notifs


BG = BackgroundManager()


@tool(name="background_run", description="Run command in background thread. Returns task_id immediately.")
def background_run(command: str) -> str:
    return BG.run(command)


@tool(name="check_background", description="Check background task status. Omit task_id to list all.")
def check_background(task_id: str | None = None) -> str:
    return BG.check(task_id)


TOOLS = OPS.get_tools() + [background_run, check_background]


def _on_before_round(messages: list):
    # 每轮调用模型前，先把后台结果注入会话上下文
    notifs = BG.drain_notifications()
    if notifs and messages:
        notif_text = "\n".join(
            f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs
        )
        messages.append({"role": "user", "content": f"<background-results>\n{notif_text}\n</background-results>"})
        messages.append({"role": "assistant", "content": "Noted background results."})


def _on_tool_result(block, output: str, results: list, messages: list):
    logger.info(f"> {block.name}: {str(output)[:200]}")
AGENT_LOOP = BaseAgentLoop(
    provider=provider,
    model=MODEL,
    system=SYSTEM,
    tools=TOOLS,
    max_tokens=8000,
    on_before_round=_on_before_round,
    on_tool_result=_on_tool_result,
)


def agent_loop(messages: list):
    AGENT_LOOP.run(messages)


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms08 >> \033[0m")
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
