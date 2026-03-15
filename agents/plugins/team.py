"""Team Plugin - Team collaboration and messaging for agents."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from ..base import tool
from .base import AgentPlugin

if TYPE_CHECKING:
    from ..agent.base_agent_loop import BaseAgentLoop


class MessageBus:
    """Inter-agent messaging system."""

    def __init__(self, inbox_dir: Path):
        self.inbox_dir = inbox_dir
        self.inbox_dir.mkdir(exist_ok=True)

    def _inbox_path(self, agent_name: str) -> Path:
        return self.inbox_dir / f"{agent_name}.jsonl"

    def send(self, to: str, content: str, from_: str = "") -> str:
        """Send a message to an agent."""
        msg = {
            "type": "message",
            "to": to,
            "from": from_,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        path = self._inbox_path(to)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        return f"Message sent to {to}"

    def broadcast(self, content: str, from_: str = "") -> str:
        """Broadcast message to all agents."""
        count = 0
        for f in self.inbox_dir.glob("*.jsonl"):
            agent_name = f.stem
            self.send(agent_name, f"[BROADCAST] {content}", from_)
            count += 1
        return f"Broadcast sent to {count} agents"

    def read(self, agent_name: str, clear: bool = False) -> list[dict]:
        """Read inbox messages."""
        path = self._inbox_path(agent_name)
        if not path.exists():
            return []

        messages = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        if clear:
            path.unlink(missing_ok=True)

        return messages


class TeammateManager:
    """Manage teammate agents."""

    def __init__(self, team_dir: Path):
        self.team_dir = team_dir
        self.team_dir.mkdir(exist_ok=True)
        self.teammates: dict[str, dict] = {}

    def spawn(self, name: str, role: str = "") -> dict:
        """Spawn a new teammate."""
        teammate = {
            "name": name,
            "role": role,
            "status": "idle",
            "spawned_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
        }
        self.teammates[name] = teammate
        return teammate

    def list(self) -> list[dict]:
        """List all teammates."""
        return list(self.teammates.values())

    def get(self, name: str) -> dict | None:
        """Get teammate by name."""
        return self.teammates.get(name)

    def idle(self, name: str) -> dict | None:
        """Mark teammate as idle."""
        teammate = self.teammates.get(name)
        if teammate:
            teammate["status"] = "idle"
            teammate["last_active"] = datetime.now().isoformat()
        return teammate

    def claim(self, name: str) -> dict | None:
        """Claim work for a teammate."""
        teammate = self.teammates.get(name)
        if teammate and teammate["status"] == "idle":
            teammate["status"] = "working"
            teammate["last_active"] = datetime.now().isoformat()
            return teammate
        return None


class TeamPlugin(AgentPlugin):
    """Plugin providing team collaboration features.

    Includes teammate management, messaging, and work claiming.
    """

    def __init__(self, team_dir: Path | None = None, inbox_dir: Path | None = None):
        super().__init__()
        if team_dir is None:
            from ..agent.s_full import TEAM_DIR
            team_dir = TEAM_DIR
        if inbox_dir is None:
            from ..agent.s_full import INBOX_DIR
            inbox_dir = INBOX_DIR
        self._teammate_manager = TeammateManager(team_dir)
        self._message_bus = MessageBus(inbox_dir)

    @property
    def name(self) -> str:
        return "team"

    def get_tools(self) -> list[Callable]:
        return [
            self._spawn_teammate,
            self._list_teammates,
            self._teammate_idle,
            self._claim_work,
            self._send_msg,
            self._broadcast,
            self._read_inbox,
        ]

    @tool(name="spawn_teammate", description="Spawn a teammate agent.")
    def _spawn_teammate(self, name: str, role: str = "") -> str:
        """Spawn a new teammate."""
        teammate = self._teammate_manager.spawn(name, role)
        return json.dumps(teammate, ensure_ascii=False)

    @tool(name="list_teammates", description="List all teammates.")
    def _list_teammates(self) -> str:
        """List all teammates."""
        teammates = self._teammate_manager.list()
        return json.dumps(teammates, ensure_ascii=False)

    @tool(name="teammate_idle", description="Mark a teammate as idle.")
    def _teammate_idle(self, name: str) -> str:
        """Mark teammate as idle."""
        teammate = self._teammate_manager.idle(name)
        if teammate:
            return json.dumps(teammate, ensure_ascii=False)
        return json.dumps({"error": f"Teammate {name} not found"})

    @tool(name="claim_work", description="Claim work for a teammate.")
    def _claim_work(self, name: str) -> str:
        """Claim work for a teammate."""
        teammate = self._teammate_manager.claim(name)
        if teammate:
            return json.dumps(teammate, ensure_ascii=False)
        return json.dumps({"error": f"Cannot claim work for {name}"})

    @tool(name="send_msg", description="Send a message to a teammate.")
    def _send_msg(self, to: str, content: str) -> str:
        """Send message to a teammate."""
        result = self._message_bus.send(to, content)
        return json.dumps({"result": result})

    @tool(name="broadcast", description="Broadcast a message to all teammates.")
    def _broadcast(self, content: str) -> str:
        """Broadcast message to all teammates."""
        result = self._message_bus.broadcast(content)
        return json.dumps({"result": result})

    @tool(name="read_inbox", description="Read messages from inbox.")
    def _read_inbox(self, agent_name: str, clear: bool = False) -> str:
        """Read inbox messages."""
        messages = self._message_bus.read(agent_name, clear)
        return json.dumps(messages, ensure_ascii=False)
