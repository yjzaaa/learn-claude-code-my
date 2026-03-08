from loguru import logger
#!/usr/bin/env python3
"""
s11_autonomous_agents.py - 自治智能体

空闲轮询任务板、自动认领未分配任务，并在上下文压缩后重注入身份信息。
本章基于 s10 的协议能力继续扩展。

    队友生命周期：
    +-------+
    | spawn |
    +---+---+
        |
        v
    +-------+  tool_use    +-------+
    | WORK  | <----------- |  LLM  |
    +---+---+              +-------+
        |
        | stop_reason != tool_use
        v
    +--------+
    | IDLE   | 每 5 秒轮询，最长 60 秒
    +---+----+
        |
        +---> 检查 inbox -> 有消息则恢复 WORK
        |
        +---> 扫描 .tasks/ -> 有未认领任务则认领并恢复 WORK
        |
        +---> 超时（60 秒）-> shutdown

    压缩后身份重注入：
    messages = [identity_block, ...remaining...]
    "You are 'coder', role: backend, team: my-team"

关键点："代理可自主发现并领取工作。"
"""

import json
import os
import threading
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
try:
    from agents.providers import create_provider_from_env
    from base import BaseAgentLoop, WorkspaceOps, tool, build_tools
except ImportError:
    from providers import create_provider_from_env
    from agents.base import BaseAgentLoop, WorkspaceOps, tool, build_tools

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
provider = create_provider_from_env()
MODEL = provider.default_model if provider else "deepseek-chat"
TEAM_DIR = WORKDIR / ".team"
INBOX_DIR = TEAM_DIR / "inbox"
TASKS_DIR = WORKDIR / ".tasks"
OPS = WorkspaceOps(workdir=WORKDIR)

POLL_INTERVAL = 5
IDLE_TIMEOUT = 60

SYSTEM = f"You are a team lead at {WORKDIR}. Teammates are autonomous -- they find work themselves."

VALID_MSG_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_response",
}

# -- 请求跟踪器 --
shutdown_requests = {}
plan_requests = {}
_tracker_lock = threading.Lock()
_claim_lock = threading.Lock()


# -- 消息总线：每位队友一个 JSONL 收件箱 --
class MessageBus:
    def __init__(self, inbox_dir: Path):
        self.dir = inbox_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def send(self, sender: str, to: str, content: str,
             msg_type: str = "message", extra: dict = None) -> str:
        if msg_type not in VALID_MSG_TYPES:
            return f"Error: Invalid type '{msg_type}'. Valid: {VALID_MSG_TYPES}"
        msg = {
            "type": msg_type,
            "from": sender,
            "content": content,
            "timestamp": time.time(),
        }
        if extra:
            msg.update(extra)
        inbox_path = self.dir / f"{to}.jsonl"
        with open(inbox_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg) + "\n")
        return f"Sent {msg_type} to {to}"

    def read_inbox(self, name: str) -> list:
        inbox_path = self.dir / f"{name}.jsonl"
        if not inbox_path.exists():
            return []
        messages = []
        for line in inbox_path.read_text(encoding="utf-8").strip().splitlines():
            if line:
                messages.append(json.loads(line))
        inbox_path.write_text("", encoding="utf-8")
        return messages

    def broadcast(self, sender: str, content: str, teammates: list) -> str:
        count = 0
        for name in teammates:
            if name != sender:
                self.send(sender, name, content, "broadcast")
                count += 1
        return f"Broadcast to {count} teammates"


BUS = MessageBus(INBOX_DIR)


# -- 任务板扫描与认领 --
def scan_unclaimed_tasks() -> list:
    TASKS_DIR.mkdir(exist_ok=True)
    unclaimed = []
    for f in sorted(TASKS_DIR.glob("task_*.json")):
        task = json.loads(f.read_text(encoding="utf-8"))
        if (task.get("status") == "pending"
                and not task.get("owner")
                and not task.get("blockedBy")):
            unclaimed.append(task)
    return unclaimed


def claim_task(task_id: int, owner: str) -> str:
    with _claim_lock:
        path = TASKS_DIR / f"task_{task_id}.json"
        if not path.exists():
            return f"Error: Task {task_id} not found"
        task = json.loads(path.read_text(encoding="utf-8"))
        task["owner"] = owner
        task["status"] = "in_progress"
        path.write_text(json.dumps(task, indent=2), encoding="utf-8")
    return f"Claimed task #{task_id} for {owner}"


# -- 压缩后身份重注入 --
def make_identity_block(name: str, role: str, team_name: str) -> dict:
    return {
        "role": "user",
        "content": f"<identity>You are '{name}', role: {role}, team: {team_name}. Continue your work.</identity>",
    }


# -- 自主队友管理器 --
class TeammateManager:
    def __init__(self, team_dir: Path):
        self.dir = team_dir
        self.dir.mkdir(exist_ok=True)
        self.config_path = self.dir / "config.json"
        self.config = self._load_config()
        self.threads = {}

    def _load_config(self) -> dict:
        if self.config_path.exists():
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        return {"team_name": "default", "members": []}

    def _save_config(self):
        self.config_path.write_text(json.dumps(self.config, indent=2), encoding="utf-8")

    def _find_member(self, name: str) -> dict:
        for m in self.config["members"]:
            if m["name"] == name:
                return m
        return None

    def _set_status(self, name: str, status: str):
        member = self._find_member(name)
        if member:
            member["status"] = status
            self._save_config()

    def spawn(self, name: str, role: str, prompt: str) -> str:
        member = self._find_member(name)
        if member:
            if member["status"] not in ("idle", "shutdown"):
                return f"Error: '{name}' is currently {member['status']}"
            member["status"] = "working"
            member["role"] = role
        else:
            member = {"name": name, "role": role, "status": "working"}
            self.config["members"].append(member)
        self._save_config()
        thread = threading.Thread(
            target=self._loop,
            args=(name, role, prompt),
            daemon=True,
        )
        self.threads[name] = thread
        thread.start()
        return f"Spawned '{name}' (role: {role})"

    def _loop(self, name: str, role: str, prompt: str):
        team_name = self.config["team_name"]
        sys_prompt = (
            f"You are '{name}', role: {role}, team: {team_name}, at {WORKDIR}. "
            f"Use idle tool when you have no more work. You will auto-claim new tasks."
        )
        messages = [{"role": "user", "content": prompt}]
        tools, handlers = self._build_teammate_toolkit(name)

        while True:
            # -- 工作阶段：常规 tool_use 循环 --
            for _ in range(50):
                inbox = BUS.read_inbox(name)
                for msg in inbox:
                    if msg.get("type") == "shutdown_request":
                        self._set_status(name, "shutdown")
                        return
                    messages.append({"role": "user", "content": json.dumps(msg)})
                try:
                    response = client.messages.create(
                        model=MODEL,
                        system=sys_prompt,
                        messages=messages,
                        tools=tools,
                        max_tokens=8000,
                    )
                except Exception:
                    self._set_status(name, "idle")
                    return
                messages.append({"role": "assistant", "content": response.content})
                if response.stop_reason != "tool_use":
                    break
                results = []
                idle_requested = False
                for block in response.content:
                    if block.type == "tool_use":
                        if block.name == "idle":
                            idle_requested = True
                            output = "Entering idle phase. Will poll for new tasks."
                        else:
                            output = self._exec(handlers, block.name, block.input)
                        logger.info(f"  [{name}] {block.name}: {str(output)[:120]}")
                        results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(output),
                        })
                messages.append({"role": "user", "content": results})
                if idle_requested:
                    break

            # -- 空闲阶段：轮询 inbox 与未认领任务 --
            self._set_status(name, "idle")
            resume = False
            polls = IDLE_TIMEOUT // max(POLL_INTERVAL, 1)
            for _ in range(polls):
                time.sleep(POLL_INTERVAL)
                inbox = BUS.read_inbox(name)
                if inbox:
                    for msg in inbox:
                        if msg.get("type") == "shutdown_request":
                            self._set_status(name, "shutdown")
                            return
                        messages.append({"role": "user", "content": json.dumps(msg)})
                    resume = True
                    break
                unclaimed = scan_unclaimed_tasks()
                if unclaimed:
                    task = unclaimed[0]
                    claim_task(task["id"], name)
                    task_prompt = (
                        f"<auto-claimed>Task #{task['id']}: {task['subject']}\n"
                        f"{task.get('description', '')}</auto-claimed>"
                    )
                    if len(messages) <= 3:
                        messages.insert(0, make_identity_block(name, role, team_name))
                        messages.insert(1, {"role": "assistant", "content": f"I am {name}. Continuing."})
                    messages.append({"role": "user", "content": task_prompt})
                    messages.append({"role": "assistant", "content": f"Claimed task #{task['id']}. Working on it."})
                    resume = True
                    break

            if not resume:
                self._set_status(name, "shutdown")
                return
            self._set_status(name, "working")

    def _exec(self, handlers: dict, tool_name: str, args: dict) -> str:
        handler = handlers.get(tool_name)
        if not handler:
            return f"Unknown tool: {tool_name}"
        try:
            return handler(**args)
        except Exception as e:
            return f"Error: {e}"

    def _build_teammate_toolkit(self, sender: str) -> tuple[list, dict]:
        # 队友工具：基础工具 + 自主代理协议工具（自动从 @tool 推断 schema）
        @tool(description="Send message to a teammate.")
        def send_message(to: str, content: str, msg_type: str = "message") -> str:
            return BUS.send(sender, to, content, msg_type)

        @tool(description="Read and drain your inbox.")
        def read_inbox() -> str:
            return json.dumps(BUS.read_inbox(sender), indent=2)

        @tool(name="shutdown_response", description="Respond to a shutdown request.")
        def shutdown_response_tool(request_id: str, approve: bool, reason: str = "") -> str:
            with _tracker_lock:
                if request_id in shutdown_requests:
                    shutdown_requests[request_id]["status"] = "approved" if approve else "rejected"
            BUS.send(
                sender,
                "lead",
                reason,
                "shutdown_response",
                {"request_id": request_id, "approve": approve},
            )
            return f"Shutdown {'approved' if approve else 'rejected'}"

        @tool(name="plan_approval", description="Submit a plan for lead approval.")
        def plan_approval_tool(plan: str) -> str:
            req_id = str(uuid.uuid4())[:8]
            with _tracker_lock:
                plan_requests[req_id] = {"from": sender, "plan": plan, "status": "pending"}
            BUS.send(
                sender,
                "lead",
                plan,
                "plan_approval_response",
                {"request_id": req_id, "plan": plan},
            )
            return f"Plan submitted (request_id={req_id}). Waiting for approval."

        @tool(description="Signal that you have no more work. Enters idle polling phase.")
        def idle() -> str:
            return "Entering idle phase. Will poll for new tasks."

        @tool(name="claim_task", description="Claim a task from the task board by ID.")
        def claim_task_tool(task_id: int) -> str:
            return claim_task(task_id, sender)

        merged_tools = build_tools(
            OPS.get_tools() + [
                send_message,
                read_inbox,
                shutdown_response_tool,
                plan_approval_tool,
                idle,
                claim_task_tool,
            ]
        )
        tools = []
        handlers = {}
        for item in merged_tools:
            handlers[item["name"]] = item["handler"]
            # OpenAI format
            tools.append({
                "type": "function",
                "function": {
                    "name": item["name"],
                    "description": item["description"],
                    "parameters": item["parameters"],
                }
            })
        return tools, handlers

    def list_all(self) -> str:
        if not self.config["members"]:
            return "No teammates."
        lines = [f"Team: {self.config['team_name']}"]
        for m in self.config["members"]:
            lines.append(f"  {m['name']} ({m['role']}): {m['status']}")
        return "\n".join(lines)

    def member_names(self) -> list:
        return [m["name"] for m in self.config["members"]]


TEAM = TeammateManager(TEAM_DIR)


# -- 主管代理协议处理函数 --
def handle_shutdown_request(teammate: str) -> str:
    req_id = str(uuid.uuid4())[:8]
    with _tracker_lock:
        shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
    BUS.send(
        "lead", teammate, "Please shut down gracefully.",
        "shutdown_request", {"request_id": req_id},
    )
    return f"Shutdown request {req_id} sent to '{teammate}'"


def handle_plan_review(request_id: str, approve: bool, feedback: str = "") -> str:
    with _tracker_lock:
        req = plan_requests.get(request_id)
    if not req:
        return f"Error: Unknown plan request_id '{request_id}'"
    with _tracker_lock:
        req["status"] = "approved" if approve else "rejected"
    BUS.send(
        "lead", req["from"], feedback, "plan_approval_response",
        {"request_id": request_id, "approve": approve, "feedback": feedback},
    )
    return f"Plan {req['status']} for '{req['from']}'"


def _check_shutdown_status(request_id: str) -> str:
    with _tracker_lock:
        return json.dumps(shutdown_requests.get(request_id, {"error": "not found"}))


# -- 主管代理工具分发：基础工具 + 自治协议工具 --
@tool
def spawn_teammate(name: str, role: str, prompt: str) -> str:
    """Spawn an autonomous teammate."""
    return TEAM.spawn(name, role, prompt)


@tool
def list_teammates() -> str:
    """List all teammates."""
    return TEAM.list_all()


@tool
def send_message(to: str, content: str, msg_type: str = "message") -> str:
    """Send a message to a teammate."""
    return BUS.send("lead", to, content, msg_type)


@tool
def read_inbox() -> str:
    """Read and drain the lead's inbox."""
    return json.dumps(BUS.read_inbox("lead"), indent=2)


@tool
def broadcast(content: str) -> str:
    """Send a message to all teammates."""
    return BUS.broadcast("lead", content, TEAM.member_names())


@tool
def shutdown_request(teammate: str) -> str:
    """Request a teammate to shut down."""
    return handle_shutdown_request(teammate)


@tool
def shutdown_response(request_id: str) -> str:
    """Check shutdown request status."""
    return _check_shutdown_status(request_id)


@tool
def plan_approval(request_id: str, approve: bool, feedback: str = "") -> str:
    """Approve or reject a teammate's plan."""
    return handle_plan_review(request_id, approve, feedback)


@tool
def idle() -> str:
    """Enter idle state (for lead -- rarely used)."""
    return "Lead does not idle."


@tool(name="claim_task")
def claim_task_tool(task_id: int) -> str:
    """Claim a task from the board by ID."""
    return claim_task(task_id, "lead")


TOOLS = OPS.get_tools() + [
    spawn_teammate,
    list_teammates,
    send_message,
    read_inbox,
    broadcast,
    shutdown_request,
    shutdown_response,
    plan_approval,
    idle,
    claim_task_tool,
]


def _on_before_round(messages: list):
    # 每轮模型调用前注入主管收件箱
    inbox = BUS.read_inbox("lead")
    if inbox:
        messages.append({
            "role": "user",
            "content": f"<inbox>{json.dumps(inbox, indent=2)}</inbox>",
        })
        messages.append({
            "role": "assistant",
            "content": "Noted inbox messages.",
        })


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
            query = input("\033[36ms11 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        if query.strip() == "/team":
            logger.info(TEAM.list_all())
            continue
        if query.strip() == "/inbox":
            logger.info(json.dumps(BUS.read_inbox("lead"), indent=2))
            continue
        if query.strip() == "/tasks":
            TASKS_DIR.mkdir(exist_ok=True)
            for f in sorted(TASKS_DIR.glob("task_*.json")):
                t = json.loads(f.read_text(encoding="utf-8"))
                marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}.get(t["status"], "[?]")
                owner = f" @{t['owner']}" if t.get("owner") else ""
                logger.info(f"  {marker} #{t['id']}: {t['subject']}{owner}")
            continue
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    logger.info(block.text)
        logger.info("")
