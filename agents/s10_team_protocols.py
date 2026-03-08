from loguru import logger
#!/usr/bin/env python3
"""
s10_team_protocols.py - 团队协议

关机协议与计划审批协议都复用同一套 request_id 关联模式，
基于 s09 的团队消息机制扩展。

    关机状态机：pending -> approved | rejected

    主管代理                          队友代理
    +---------------------+          +---------------------+
    | shutdown_request     |          |                     |
    | {                    | -------> | 收到请求            |
    |   request_id: abc    |          | 是否同意关闭？      |
    | }                    |          |                     |
    +---------------------+          +---------------------+
                                             |
    +---------------------+          +-------v-------------+
    | shutdown_response    | <------- | shutdown_response   |
    | {                    |          | {                   |
    |   request_id: abc    |          |   request_id: abc   |
    |   approve: true      |          |   approve: true     |
    | }                    |          | }                   |
    +---------------------+          +---------------------+
            |
            v
    status -> "shutdown"，线程停止

    计划审批状态机：pending -> approved | rejected

    队友代理                          主管代理
    +---------------------+          +---------------------+
    | plan_approval        |          |                     |
    | submit: {plan:"..."}| -------> | 审核计划文本        |
    +---------------------+          | 同意/拒绝？         |
                                     +---------------------+
                                             |
    +---------------------+          +-------v-------------+
    | plan_approval_resp   | <------- | plan_approval       |
    | {approve: true}      |          | review: {req_id,    |
    +---------------------+          |   approve: true}     |
                                     +---------------------+

    跟踪表：{request_id: {"target|from": name, "status": "pending|..."}}

关键点："同一 request_id 关联模式，复用于两个协议域。"
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
OPS = WorkspaceOps(workdir=WORKDIR)

SYSTEM = f"You are a team lead at {WORKDIR}. Manage teammates with shutdown and plan approval protocols."

VALID_MSG_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_response",
}

# -- 请求跟踪器：通过 request_id 关联请求与响应 --
shutdown_requests = {}
plan_requests = {}
_tracker_lock = threading.Lock()


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


# -- 队友管理：支持关机协议与计划审批协议 --
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
            target=self._teammate_loop,
            args=(name, role, prompt),
            daemon=True,
        )
        self.threads[name] = thread
        thread.start()
        return f"Spawned '{name}' (role: {role})"

    def _teammate_loop(self, name: str, role: str, prompt: str):
        sys_prompt = (
            f"You are '{name}', role: {role}, at {WORKDIR}. "
            f"Submit plans via plan_approval before major work. "
            f"Respond to shutdown_request with shutdown_response."
        )
        messages = [{"role": "user", "content": prompt}]
        tools, handlers = self._build_teammate_toolkit(name)
        should_exit = False
        for _ in range(50):
            inbox = BUS.read_inbox(name)
            for msg in inbox:
                messages.append({"role": "user", "content": json.dumps(msg)})
            if should_exit:
                break
            try:
                response = client.messages.create(
                    model=MODEL,
                    system=sys_prompt,
                    messages=messages,
                    tools=tools,
                    max_tokens=8000,
                )
            except Exception:
                break
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                break
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    output = self._exec(handlers, block.name, block.input)
                    logger.info(f"  [{name}] {block.name}: {str(output)[:120]}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(output),
                    })
                    if block.name == "shutdown_response" and block.input.get("approve"):
                        should_exit = True
            messages.append({"role": "user", "content": results})
        member = self._find_member(name)
        if member:
            member["status"] = "shutdown" if should_exit else "idle"
            self._save_config()

    def _exec(self, handlers: dict, tool_name: str, args: dict) -> str:
        handler = handlers.get(tool_name)
        if not handler:
            return f"Unknown tool: {tool_name}"
        try:
            return handler(**args)
        except Exception as e:
            return f"Error: {e}"

    def _build_teammate_toolkit(self, sender: str) -> tuple[list, dict]:
        # 队友工具：基础工具 + 协议工具（自动从 @tool 推断 schema）
        @tool(description="Send message to a teammate.")
        def send_message(to: str, content: str, msg_type: str = "message") -> str:
            return BUS.send(sender, to, content, msg_type)

        @tool(description="Read and drain your inbox.")
        def read_inbox() -> str:
            return json.dumps(BUS.read_inbox(sender), indent=2)

        @tool(name="shutdown_response", description="Respond to a shutdown request. Approve to shut down, reject to keep working.")
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

        @tool(name="plan_approval", description="Submit a plan for lead approval. Provide plan text.")
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
            return f"Plan submitted (request_id={req_id}). Waiting for lead approval."

        merged_tools = build_tools(
            OPS.get_tools() + [send_message, read_inbox, shutdown_response_tool, plan_approval_tool]
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
    return f"Shutdown request {req_id} sent to '{teammate}' (status: pending)"


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


# -- 主管代理工具分发：基础工具 + 协议工具 --
@tool
def spawn_teammate(name: str, role: str, prompt: str) -> str:
    """Spawn a persistent teammate."""
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
    """Request a teammate to shut down gracefully. Returns a request_id for tracking."""
    return handle_shutdown_request(teammate)


@tool
def shutdown_response(request_id: str) -> str:
    """Check the status of a shutdown request by request_id."""
    return _check_shutdown_status(request_id)


@tool
def plan_approval(request_id: str, approve: bool, feedback: str = "") -> str:
    """Approve or reject a teammate's plan. Provide request_id + approve + optional feedback."""
    return handle_plan_review(request_id, approve, feedback)


TOOLS = OPS.get_tools() + [
    spawn_teammate,
    list_teammates,
    send_message,
    read_inbox,
    broadcast,
    shutdown_request,
    shutdown_response,
    plan_approval,
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
            query = input("\033[36ms10 >> \033[0m")
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
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    logger.info(block.text)
        logger.info("")
