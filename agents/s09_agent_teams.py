#!/usr/bin/env python3
"""
s09_agent_teams.py - 智能体团队

通过文件 JSONL 收件箱管理持久化命名代理。每个队友在独立线程运行，
通过追加写入的收件箱通信。

    子代理（s04）：spawn -> execute -> 返回摘要 -> 销毁
    队友代理（s09）：spawn -> work -> idle -> work -> ... -> shutdown

    .team/config.json                   .team/inbox/
    +----------------------------+      +------------------+
    | {"team_name": "default",   |      | alice.jsonl      |
    |  "members": [              |      | bob.jsonl        |
    |    {"name":"alice",        |      | lead.jsonl       |
    |     "role":"coder",        |      +------------------+
    |     "status":"idle"}       |
    |  ]}                        |      send_message("alice", "fix bug")：
    +----------------------------+        open("alice.jsonl", "a").write(msg)

                                        read_inbox("alice")：
    spawn_teammate("alice","coder",...)   msgs = [json.loads(l) for l in ...]
         |                                open("alice.jsonl", "w").close()
         v                                return msgs  # 读取后清空
    线程：alice               线程：bob
    +------------------+      +------------------+
    | agent_loop       |      | agent_loop       |
    | 状态：working    |      | 状态：idle       |
    | ... 执行工具 ... |      | ... 等待中 ...   |
    | 状态 -> idle     |      |                  |
    +------------------+      +------------------+

    5 种消息类型（此处全部声明，部分在后续章节处理）：
    +-------------------------+-----------------------------------+
    | message                 | 普通文本消息                      |
    | broadcast               | 向所有队友广播                    |
    | shutdown_request        | 请求优雅停机（s10）               |
    | shutdown_response       | 同意/拒绝停机（s10）              |
    | plan_approval_response  | 同意/拒绝计划（s10）              |
    +-------------------------+-----------------------------------+

关键点："可互相通信的持久化队友代理。"
"""

import json
import os
import threading
import time
from pathlib import Path

from dotenv import load_dotenv
try:
    from client import get_client, get_model
    from base import BaseAgentLoop, WorkspaceOps, tool, build_tools
except ImportError:
    from agents.client import get_client, get_model
    from agents.base import BaseAgentLoop, WorkspaceOps, tool, build_tools

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = get_client()
MODEL = get_model()
TEAM_DIR = WORKDIR / ".team"
INBOX_DIR = TEAM_DIR / "inbox"
OPS = WorkspaceOps(workdir=WORKDIR)

SYSTEM = f"You are a team lead at {WORKDIR}. Spawn teammates and communicate via inboxes."

VALID_MSG_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_response",
}


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


# -- 队友管理：通过 config.json 管理持久化成员 --
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
            f"Use send_message to communicate. Complete your task."
        )
        messages = [{"role": "user", "content": prompt}]
        tools, handlers = self._build_teammate_toolkit(name)
        for _ in range(50):
            inbox = BUS.read_inbox(name)
            for msg in inbox:
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
                break
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                break
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    output = self._exec(handlers, block.name, block.input)
                    print(f"  [{name}] {block.name}: {str(output)[:120]}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(output),
                    })
            messages.append({"role": "user", "content": results})
        member = self._find_member(name)
        if member and member["status"] != "shutdown":
            member["status"] = "idle"
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
        # 队友可用工具：基础工具 + 消息收发（自动从 @tool 推断 schema）
        @tool(description="Send message to a teammate.")
        def send_message(to: str, content: str, msg_type: str = "message") -> str:
            return BUS.send(sender, to, content, msg_type)

        @tool(description="Read and drain your inbox.")
        def read_inbox() -> str:
            return json.dumps(BUS.read_inbox(sender), indent=2)

        merged_tools = build_tools(OPS.get_tools() + [send_message, read_inbox])
        tools = []
        handlers = {}
        for item in merged_tools:
            handlers[item["name"]] = item["handler"]
            tools.append(
                {
                    "name": item["name"],
                    "description": item["description"],
                    "input_schema": item["input_schema"],
                }
            )
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


# -- 主管代理工具分发：基础工具 + 团队协作工具 --
@tool
def spawn_teammate(name: str, role: str, prompt: str) -> str:
    """Spawn a persistent teammate that runs in its own thread."""
    return TEAM.spawn(name, role, prompt)


@tool
def list_teammates() -> str:
    """List all teammates with name, role, status."""
    return TEAM.list_all()


@tool
def send_message(to: str, content: str, msg_type: str = "message") -> str:
    """Send a message to a teammate's inbox."""
    return BUS.send("lead", to, content, msg_type)


@tool
def read_inbox() -> str:
    """Read and drain the lead's inbox."""
    return json.dumps(BUS.read_inbox("lead"), indent=2)


@tool
def broadcast(content: str) -> str:
    """Send a message to all teammates."""
    return BUS.broadcast("lead", content, TEAM.member_names())


TOOLS = OPS.get_tools() + [
    spawn_teammate,
    list_teammates,
    send_message,
    read_inbox,
    broadcast,
]


def _on_before_round(messages: list):
    # 每轮模型调用前先注入 lead 收件箱消息
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
    print(f"> {block.name}: {str(output)[:200]}")


AGENT_LOOP = BaseAgentLoop(
    client=client,
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
            query = input("\033[36ms09 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        if query.strip() == "/team":
            print(TEAM.list_all())
            continue
        if query.strip() == "/inbox":
            print(json.dumps(BUS.read_inbox("lead"), indent=2))
            continue
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()


