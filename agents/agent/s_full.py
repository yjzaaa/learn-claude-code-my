#!/usr/bin/env python3
"""
s_full.py - Full Featured Agent

Capstone implementation combining all mechanisms:
- Skill loading (s05)
- Tool use with bash/read/write/edit (s02)
- Subagent for task decomposition (s04)
- Hook support for state management
- Todo management (s03)
- Context compaction support (s06)
- Task system (s07)
- Background task execution (s08)
- Team messaging and teammate management (s09/s11)
- Shutdown protocol (s10)
- Plan approval gate (s10)

This is the production-ready full-capability agent.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Any

from dotenv import load_dotenv
from loguru import logger

try:
    from agents.providers import create_provider_from_env, LiteLLMProvider
    from agents.base import BaseAgentLoop, WorkspaceOps, tool, build_tools_and_handlers
    from agents.core.s05_skill_loading import SKILL_LOADER
    from agents.base.abstract import HookName
    from agents.monitoring.bridge.composite import CompositeMonitoringBridge
    from agents.monitoring.services import event_bus
    from agents.monitoring.domain.payloads import (
        SubagentStartedPayload,
        SubagentCompletedPayload,
        SubagentFailedPayload,
    )
    from agents.models.common_types import BackgroundTaskStatus
except ImportError:
    from providers import create_provider_from_env, LiteLLMProvider
    from base import BaseAgentLoop, WorkspaceOps, tool, build_tools_and_handlers
    from core.s05_skill_loading import SKILL_LOADER
    from base.abstract import HookName
    from monitoring.bridge.composite import CompositeMonitoringBridge
    from monitoring.services import event_bus
    from monitoring.domain.payloads import (
        SubagentStartedPayload,
        SubagentCompletedPayload,
        SubagentFailedPayload,
    )
    from models.common_types import BackgroundTaskStatus

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"
TEAM_DIR = WORKDIR / ".team"
INBOX_DIR = TEAM_DIR / "inbox"
TASKS_DIR = WORKDIR / ".tasks"

# Ensure directories exist
TEAM_DIR.mkdir(exist_ok=True)
INBOX_DIR.mkdir(exist_ok=True)
TASKS_DIR.mkdir(exist_ok=True)

provider = create_provider_from_env()
MODEL = provider.default_model if provider else "deepseek-chat"
OPS = WorkspaceOps(workdir=WORKDIR)

SYSTEM = f"""You are a coding agent at {WORKDIR}. Use tools to solve tasks.

Runtime OS is Windows.
Skills available:
{SKILL_LOADER.get_descriptions()}

Skill usage policy:
1. If the user explicitly asks to use a skill, you MUST call load_skill(name) before answering.
2. After load_skill(name), read the returned manifest and only load extra references/scripts when required.
3. Do not claim a skill is unavailable unless load_skill returns an explicit error.

Progressive loading rule:
1. Call load_skill(name) first to get overview + manifest.
2. Call load_skill_reference(name, path) for specific docs.
3. Call load_skill_script(name, path) for executable script details.
Only load extra files when needed.

Todo management:
- Use todo tool to track multi-step tasks
- Update todo status as you complete items
- Keep exactly one in_progress item at a time
"""

# Constants
TOKEN_THRESHOLD = 100000
POLL_INTERVAL = 5
IDLE_TIMEOUT = 60
MAX_TODO_ITEMS = 20

VALID_MSG_TYPES = {"message", "broadcast", "shutdown_request",
                   "shutdown_response", "plan_approval_response"}


# ===== SECTION: Base Tools =====

def safe_path(p: str) -> Path:
    """Ensure path is within workspace."""
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


# ===== SECTION: Todo Manager (s03) =====

class TodoManager:
    """Manage todo items with validation."""

    def __init__(self):
        self.items: list[dict] = []

    def update(self, items: list) -> str:
        """Update todo items with validation."""
        validated, in_progress_count = [], 0
        for i, item in enumerate(items):
            content = str(item.get("content", "")).strip()
            status = str(item.get("status", "pending")).lower()
            af = str(item.get("activeForm", "")).strip()

            if not content:
                raise ValueError(f"Item {i}: content required")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Item {i}: invalid status '{status}'")
            if not af:
                raise ValueError(f"Item {i}: activeForm required")
            if status == "in_progress":
                in_progress_count += 1

            validated.append({"content": content, "status": status, "activeForm": af})

        if len(validated) > MAX_TODO_ITEMS:
            raise ValueError(f"Max {MAX_TODO_ITEMS} todos")
        if in_progress_count > 1:
            raise ValueError("Only one in_progress allowed")

        self.items = validated
        return self.render()

    def render(self) -> str:
        """Render todos as string."""
        if not self.items:
            return "No todos."
        lines = []
        for item in self.items:
            mark = {"completed": "[x]", "in_progress": "[>]", "pending": "[ ]"}.get(item["status"], "[?]")
            suffix = f" <- {item['activeForm']}" if item["status"] == "in_progress" else ""
            lines.append(f"{mark} {item['content']}{suffix}")
        done = sum(1 for t in self.items if t["status"] == "completed")
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines)

    def has_open_items(self) -> bool:
        return any(item.get("status") != "completed" for item in self.items)


# ===== SECTION: Subagent (s04) =====

class SubagentRunner:
    """Run subagents for task decomposition."""

    def __init__(self, provider: LiteLLMProvider, model: str):
        self.provider = provider
        self.model = model

    async def run(self, prompt: str, agent_type: str = "Explore", name: str = "", dialog_id: str = None) -> str:
        """Run a subagent with limited tools.

        Args:
            prompt: The task description
            agent_type: Type of subagent
            name: Custom name for the subagent (e.g., "CodeAnalyzer")
            dialog_id: The dialog ID for monitoring events (required for proper event routing)
        """
        # Ensure all parameters have valid values
        prompt = prompt or ""
        agent_type = agent_type or "Explore"
        name = name or ""

        # Generate subagent identifier
        subagent_id = name or f"Subagent_{agent_type}_{id(self) % 10000}"
        agent_name = f"Subagent:{agent_type}:{subagent_id}"

        # Import monitoring components
        try:
            from ..monitoring.domain import MonitoringEvent, EventType, EventPriority
            from ..monitoring.services import event_bus
            from ..session.runtime_context import get_current_dialog_id
            monitoring_available = True
        except ImportError:
            monitoring_available = False

        # Get current dialog_id from context or use provided one
        # Note: In sub-thread, context variables are not inherited, so we need the explicit parameter
        if dialog_id is None:
            dialog_id = get_current_dialog_id() or "system"
            if dialog_id == "system":
                logger.warning(f"[SubagentRunner] No dialog_id available for {agent_name}, events may not reach frontend")

        # Emit SUBAGENT_STARTED event
        if monitoring_available:
            try:
                started_payload = SubagentStartedPayload(
                    subagent_name=subagent_id,
                    subagent_type=agent_type,
                    task_preview=prompt[:200] if prompt else ""
                )
                event = MonitoringEvent(
                    type=EventType.SUBAGENT_STARTED,
                    dialog_id=dialog_id,
                    source=agent_name,
                    context_id=str(uuid.uuid4()),
                    priority=EventPriority.HIGH,
                    payload=started_payload.model_dump()
                )
                # Use thread-safe emit_sync to ensure events are processed even in sub-thread
                event_bus.emit_sync(event)
                logger.info(f"[SubagentRunner] SUBAGENT_STARTED event emitted for {agent_name}")
            except Exception as e:
                logger.warning(f"[SubagentRunner] Failed to emit SUBAGENT_STARTED: {e}")

        sub_tools = [
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "Run command.",
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read file.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"]
                    }
                }
            },
        ]

        if agent_type != "Explore":
            sub_tools.extend([
                {
                    "type": "function",
                    "function": {
                        "name": "write_file",
                        "description": "Write file.",
                        "parameters": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                            "required": ["path", "content"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "edit_file",
                        "description": "Edit file.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "old_text": {"type": "string"},
                                "new_text": {"type": "string"}
                            },
                            "required": ["path", "old_text", "new_text"]
                        }
                    }
                },
            ])

        sub_handlers = {
            "bash": lambda **kw: run_bash(kw["command"]),
            "read_file": lambda **kw: run_read(kw["path"]),
            "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
            "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
        }

        sub_msgs = [{"role": "user", "content": prompt}]
        final_content = ""

        try:
            for _ in range(30):
                content = ""
                tool_calls = []

                async for chunk in self.provider.chat_stream(
                    messages=sub_msgs,
                    tools=sub_tools,
                    model=self.model,
                    max_tokens=4000,
                ):
                    if chunk.is_content:
                        content += chunk.content
                    elif chunk.is_tool_call:
                        tool_calls.append(chunk.tool_call)
                    elif chunk.is_done:
                        break

                if content:
                    sub_msgs.append({"role": "assistant", "content": content})
                    final_content = content

                if not tool_calls:
                    break

                results = []
                for tc in tool_calls:
                    handler = sub_handlers.get(tc.name, lambda **kw: "Unknown tool")
                    result = handler(**tc.arguments)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": str(result)[:50000]
                    })

                sub_msgs.append({"role": "user", "content": json.dumps(results)})

            # Emit SUBAGENT_COMPLETED event
            result_content = final_content or "(no summary)"
            logger.info(f"[SubagentRunner] Subagent {agent_name} completed with result: {result_content[:100]}...")
            if monitoring_available:
                try:
                    completed_payload = SubagentCompletedPayload(
                        subagent_name=subagent_id,
                        subagent_type=agent_type,
                        result_preview=result_content[:200] if result_content else ""
                    )
                    event = MonitoringEvent(
                        type=EventType.SUBAGENT_COMPLETED,
                        dialog_id=dialog_id,
                        source=agent_name,
                        context_id=str(uuid.uuid4()),
                        priority=EventPriority.HIGH,
                        payload=completed_payload.model_dump()
                    )
                    # Use thread-safe emit_sync
                    event_bus.emit_sync(event)
                    logger.info(f"[SubagentRunner] SUBAGENT_COMPLETED event emitted for {agent_name}")
                except Exception as e:
                    logger.warning(f"[SubagentRunner] Failed to emit SUBAGENT_COMPLETED: {e}")

            return result_content
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[SubagentRunner] Subagent {agent_name} failed: {error_msg}")
            # Emit SUBAGENT_FAILED event
            if monitoring_available:
                try:
                    failed_payload = SubagentFailedPayload(
                        subagent_name=subagent_id,
                        subagent_type=agent_type,
                        error=error_msg
                    )
                    event = MonitoringEvent(
                        type=EventType.SUBAGENT_FAILED,
                        dialog_id=dialog_id,
                        source=agent_name,
                        context_id=str(uuid.uuid4()),
                        priority=EventPriority.CRITICAL,
                        payload=failed_payload.model_dump()
                    )
                    # Use thread-safe emit_sync
                    event_bus.emit_sync(event)
                    logger.info(f"[SubagentRunner] SUBAGENT_FAILED event emitted for {agent_name}")
                except Exception as emit_err:
                    logger.warning(f"[SubagentRunner] Failed to emit SUBAGENT_FAILED: {emit_err}")
            return f"(subagent failed: {e})"


# ===== SECTION: Task Manager (s07) =====

class TaskManager:
    """Persistent task management."""

    def __init__(self, tasks_dir: Path):
        self.tasks_dir = tasks_dir
        self.tasks_dir.mkdir(exist_ok=True)

    def _task_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.json"

    def create(self, title: str, description: str = "", assignee: str = "") -> dict:
        """Create a new task."""
        task_id = f"task_{int(time.time() * 1000)}"
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "status": "open",
            "assignee": assignee,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._task_path(task_id).write_text(json.dumps(task, indent=2), encoding="utf-8")
        return task

    def get(self, task_id: str) -> dict | None:
        """Get task by ID."""
        path = self._task_path(task_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def update(self, task_id: str, **updates) -> dict | None:
        """Update task fields."""
        task = self.get(task_id)
        if not task:
            return None
        task.update(updates)
        task["updated_at"] = datetime.now().isoformat()
        self._task_path(task_id).write_text(json.dumps(task, indent=2), encoding="utf-8")
        return task

    def list(self, status: str = None) -> list[dict]:
        """List all tasks, optionally filtered by status."""
        tasks = []
        for f in self.tasks_dir.glob("*.json"):
            try:
                task = json.loads(f.read_text(encoding="utf-8"))
                if status is None or task.get("status") == status:
                    tasks.append(task)
            except Exception:
                continue
        return sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True)


# ===== SECTION: Background Manager (s08) =====

class BackgroundManager:
    """Manage background task execution."""

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.tasks: dict[str, dict] = {}

    def run(self, command: str, timeout: int = 300) -> str:
        """Start a background command."""
        task_id = f"bg_{int(time.time() * 1000)}"
        self.tasks[task_id] = {
            "id": task_id,
            "command": command,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "result": None,
        }

        def execute():
            try:
                r = subprocess.run(
                    command, shell=True, cwd=WORKDIR,
                    capture_output=True, text=True, timeout=timeout
                )
                self.tasks[task_id]["status"] = "completed"
                self.tasks[task_id]["result"] = (r.stdout + r.stderr).strip()[:50000]
                self.tasks[task_id]["completed_at"] = datetime.now().isoformat()
            except subprocess.TimeoutExpired:
                self.tasks[task_id]["status"] = "timeout"
                self.tasks[task_id]["result"] = f"Timeout ({timeout}s)"
            except Exception as e:
                self.tasks[task_id]["status"] = "error"
                self.tasks[task_id]["result"] = str(e)

        self.tasks[task_id]["future"] = self.executor.submit(execute)
        return task_id

    def check(self, task_id: str) -> dict:
        """Check background task status."""
        task = self.tasks.get(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}
        status = BackgroundTaskStatus(
            id=task["id"],
            status=task["status"],
            command=task["command"],
            result=task.get("result"),
            started_at=task.get("started_at"),
            completed_at=task.get("completed_at"),
        )
        return status.model_dump()


# ===== SECTION: Message Bus (s09) =====

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


# ===== SECTION: Teammate Manager (s09/s11) =====

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


# ===== SECTION: Shutdown & Plan (s10) =====

class ShutdownProtocol:
    """Handle graceful shutdown."""

    def __init__(self):
        self.pending_requests: dict[str, dict] = {}

    def request(self, agent_name: str) -> str:
        """Request shutdown."""
        request_id = str(uuid.uuid4())
        self.pending_requests[request_id] = {
            "agent": agent_name,
            "status": "pending",
            "requested_at": datetime.now().isoformat(),
        }
        return request_id

    def respond(self, request_id: str, approved: bool) -> str:
        """Respond to shutdown request."""
        req = self.pending_requests.get(request_id)
        if not req:
            return f"Unknown request: {request_id}"
        req["status"] = "approved" if approved else "rejected"
        req["responded_at"] = datetime.now().isoformat()
        return f"Shutdown {req['status']}"


class PlanGate:
    """Plan approval gate."""

    def __init__(self):
        self.pending_plans: dict[str, dict] = {}

    def submit(self, plan: str) -> str:
        """Submit a plan for approval."""
        plan_id = f"plan_{int(time.time() * 1000)}"
        self.pending_plans[plan_id] = {
            "id": plan_id,
            "plan": plan,
            "status": "pending",
            "submitted_at": datetime.now().isoformat(),
        }
        return plan_id

    def review(self, plan_id: str, approve: bool, feedback: str = "") -> dict | None:
        """Review a plan."""
        plan = self.pending_plans.get(plan_id)
        if not plan:
            return None
        plan["status"] = "approved" if approve else "rejected"
        plan["feedback"] = feedback
        plan["reviewed_at"] = datetime.now().isoformat()
        return plan


# ===== SECTION: Helper Functions =====

def run_bash(command: str) -> str:
    """Run bash command safely (original version without monitoring)."""
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def run_read(path: str, limit: int = None) -> str:
    """Read file with limit."""
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    """Write file."""
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    """Edit file."""
    try:
        fp = safe_path(path)
        c = fp.read_text(encoding="utf-8")
        if old_text not in c:
            return f"Error: Text not found in {path}"
        fp.write_text(c.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


# ===== SECTION: Tool Functions =====

@tool(name="load_skill", description="Load full skill content by skill name.")
def load_skill(name: str) -> str:
    return SKILL_LOADER.get_content(name)


@tool(name="load_skill_reference", description="Load a references document from a skill; omit path to list docs.")
def load_skill_reference(name: str, path: str = "") -> str:
    return SKILL_LOADER.get_references_content(name, path)


@tool(name="load_skill_script", description="Load a scripts file from a skill; omit path to list scripts.")
def load_skill_script(name: str, path: str = "") -> str:
    return SKILL_LOADER.get_scripts_content(name, path)


@tool(name="todo", description="""Manage todo items. Examples:
- {"items": [{"id": "1", "content": "Task", "status": "in_progress", "activeForm": "Doing task"}]}
- {"items": []} to clear all
Valid statuses: pending, in_progress, completed""")
def manage_todo(items: list[dict[str, Any]]) -> str:
    """Manage todo items for tracking multi-step tasks."""
    try:
        from agents.session.todo_hitl import todo_store
        from agents.session.runtime_context import get_current_dialog_id
        from agents.models.responses import TodoUpdateResponse

        dialog_id = get_current_dialog_id()
        if not dialog_id:
            return TodoUpdateResponse(
                success=False,
                error="No active dialog"
            ).model_dump_json()

        success, error = todo_store.update_todos(dialog_id, items)
        if success:
            return TodoUpdateResponse(
                success=True,
                dialog_id=dialog_id,
                item_count=len(items),
                items=items
            ).model_dump_json()
        else:
            return TodoUpdateResponse(
                success=False,
                error=error
            ).model_dump_json()
    except Exception as e:
        return TodoUpdateResponse(
            success=False,
            error=str(e)
        ).model_dump_json()


@tool(name="context_compact", description="Compact conversation context when approaching token limit.")
def context_compact(summary: str) -> str:
    """Signal that context should be compacted."""
    from agents.models.responses import ContextCompactResponse
    return ContextCompactResponse(summary=summary).model_dump_json()


@tool(name="subagent", description="Spawn a subagent for task decomposition. agent_type: Explore|General|Code|Test|Review")
def subagent(
    prompt: str,
    agent_type: str = "Explore",
    name: str = ""
) -> str:
    """Run a subagent to handle sub-tasks.

    Args:
        prompt: The task description for the subagent
        agent_type: Type of subagent (Explore|General|Code|Test|Review)
        name: Optional custom name for the subagent (e.g., "CodeAnalyzer", "TestWriter")
    """
    # Ensure parameters are not None
    prompt = prompt or ""
    agent_type = agent_type or "Explore"
    name = name or ""

    # 获取当前的 dialog_id（必须在主线程中获取）
    try:
        from ..session.runtime_context import get_current_dialog_id
        dialog_id = get_current_dialog_id()
    except ImportError:
        try:
            from agents.session.runtime_context import get_current_dialog_id
            dialog_id = get_current_dialog_id()
        except ImportError:
            dialog_id = None

    if dialog_id is None:
        logger.warning("[subagent] No dialog_id available, monitoring events may not reach frontend")
        dialog_id = "system"

    runner = SubagentRunner(provider, MODEL)
    try:
        # 兼容已有事件循环的情况
        try:
            loop = asyncio.get_running_loop()
            # 如果在运行中的事件循环中，使用 create_task 并等待
            if loop.is_running():
                # 创建一个新任务并等待完成
                import concurrent.futures
                # 传递 dialog_id 到子线程
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, runner.run(prompt, agent_type, name, dialog_id))
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(runner.run(prompt, agent_type, name, dialog_id))
        except RuntimeError:
            # 没有运行中的事件循环，直接使用 asyncio.run
            return asyncio.run(runner.run(prompt, agent_type, name, dialog_id))
    except Exception as e:
        return f"Subagent error: {e}"


@tool(name="task_create", description="Create a persistent task.")
def task_create(title: str, description: str = "", assignee: str = "") -> str:
    """Create a new task."""
    tm = TaskManager(TASKS_DIR)
    task = tm.create(title, description, assignee)
    return json.dumps(task, ensure_ascii=False)


@tool(name="task_get", description="Get task by ID.")
def task_get(task_id: str) -> str:
    """Get task details."""
    tm = TaskManager(TASKS_DIR)
    task = tm.get(task_id)
    return json.dumps(task, ensure_ascii=False) if task else f"Task {task_id} not found"


@tool(name="task_update", description="Update task status.")
def task_update(task_id: str, status: str = "", assignee: str = "") -> str:
    """Update task fields."""
    tm = TaskManager(TASKS_DIR)
    updates = {}
    if status:
        updates["status"] = status
    if assignee:
        updates["assignee"] = assignee
    task = tm.update(task_id, **updates)
    return json.dumps(task, ensure_ascii=False) if task else f"Task {task_id} not found"


@tool(name="task_list", description="List tasks. Optionally filter by status.")
def task_list(status: str = "") -> str:
    """List all tasks."""
    tm = TaskManager(TASKS_DIR)
    tasks = tm.list(status or None)
    return json.dumps(tasks, ensure_ascii=False)


@tool(name="bg_run", description="Run a command in background. Returns task_id.")
def bg_run(command: str, timeout: int = 300) -> str:
    """Run command in background."""
    bm = BackgroundManager()
    task_id = bm.run(command, timeout)
    return json.dumps({"task_id": task_id, "status": "running"}, ensure_ascii=False)


@tool(name="bg_check", description="Check background task status.")
def bg_check(task_id: str) -> str:
    """Check background task."""
    bm = BackgroundManager()
    result = bm.check(task_id)
    return json.dumps(result, ensure_ascii=False)


@tool(name="send_msg", description="Send message to a teammate.")
def send_msg(to: str, content: str) -> str:
    """Send message to teammate."""
    bus = MessageBus(INBOX_DIR)
    return bus.send(to, content)


@tool(name="broadcast", description="Broadcast message to all teammates.")
def broadcast(content: str) -> str:
    """Broadcast to all."""
    bus = MessageBus(INBOX_DIR)
    return bus.broadcast(content)


@tool(name="read_inbox", description="Read inbox messages. Set clear=True to empty after reading.")
def read_inbox(clear: bool = False) -> str:
    """Read inbox."""
    bus = MessageBus(INBOX_DIR)
    messages = bus.read("default", clear)
    return json.dumps(messages, ensure_ascii=False)


@tool(name="spawn_teammate", description="Spawn a new teammate agent.")
def spawn_teammate(name: str, role: str = "") -> str:
    """Spawn teammate."""
    tm = TeammateManager(TEAM_DIR)
    teammate = tm.spawn(name, role)
    return json.dumps(teammate, ensure_ascii=False)


@tool(name="list_teammates", description="List all teammates.")
def list_teammates() -> str:
    """List teammates."""
    tm = TeammateManager(TEAM_DIR)
    teammates = tm.list()
    return json.dumps(teammates, ensure_ascii=False)


@tool(name="teammate_idle", description="Mark teammate as idle.")
def teammate_idle(name: str) -> str:
    """Mark teammate idle."""
    tm = TeammateManager(TEAM_DIR)
    teammate = tm.idle(name)
    return json.dumps(teammate, ensure_ascii=False) if teammate else f"Teammate {name} not found"


@tool(name="claim_work", description="Claim work for a teammate.")
def claim_work(name: str) -> str:
    """Claim work for teammate."""
    tm = TeammateManager(TEAM_DIR)
    teammate = tm.claim(name)
    return json.dumps(teammate, ensure_ascii=False) if teammate else f"Cannot claim work for {name}"


@tool(name="submit_plan", description="Submit a plan for approval. Returns plan_id.")
def submit_plan(plan: str) -> str:
    """Submit plan for approval."""
    pg = PlanGate()
    plan_id = pg.submit(plan)
    return json.dumps({"plan_id": plan_id, "status": "pending"}, ensure_ascii=False)


@tool(name="review_plan", description="Approve or reject a plan.")
def review_plan(plan_id: str, approve: bool, feedback: str = "") -> str:
    """Review a plan."""
    pg = PlanGate()
    result = pg.review(plan_id, approve, feedback)
    return json.dumps(result, ensure_ascii=False) if result else f"Plan {plan_id} not found"


# ===== SECTION: SFullAgent Class =====

class SFullAgent(BaseAgentLoop):
    """
    Full-featured agent with all capabilities:
    - Skill loading (s05)
    - Subagent decomposition (s04)
    - Task management (s07)
    - Background execution (s08)
    - Team messaging (s09)
    - Teammate management (s09/s11)
    - Plan approval (s10)
    - Todo management (s03)
    - Context compaction (s06)
    """

    def __init__(
        self,
        *,
        max_tokens: int = 8000,
        max_rounds: int = 25,
        **kwargs
    ) -> None:
        # Build complete tool set
        base_tools = OPS.get_tools(as_dict=True)

        # 使用带监控的 bash 工具覆盖默认的 bash 工具
        @tool(name="bash", description="Run a command in Windows PowerShell with monitoring.")
        def monitored_bash(command: str) -> str:
            return self._run_bash_with_monitoring(command)

        extra_tools = [
            monitored_bash,  # 使用带监控的版本覆盖
            load_skill, load_skill_reference, load_skill_script,
            manage_todo, context_compact,
            subagent,
            task_create, task_get, task_update, task_list,
            bg_run, bg_check,
            send_msg, broadcast, read_inbox,
            spawn_teammate, list_teammates, teammate_idle, claim_work,
            submit_plan, review_plan,
        ]

        # 合并工具，extra_tools 会覆盖 base_tools 中的同名工具
        if isinstance(base_tools, dict):
            # 移除默认的 bash 工具，使用我们的监控版本
            base_tools.pop("bash", None)
            tool_functions = list(base_tools.values()) + extra_tools
        else:
            tool_functions = list(base_tools) + extra_tools

        tools, tool_handlers = build_tools_and_handlers(tool_functions)

        # Enhanced system prompt
        system = SYSTEM + """

Advanced capabilities:
- Use subagent() to decompose complex tasks
- Use task_* tools for persistent task tracking
- Use bg_run/bg_check for long-running commands
- Use spawn_teammate/claim_work for multi-agent collaboration
- Use send_msg/broadcast for team communication
- Use submit_plan/review_plan for important decisions

When to use subagent:
- Complex research tasks
- Multi-file exploration
- Independent sub-tasks that can run in parallel

When to use bg_run:
- Commands that take >30 seconds
- Build processes
- Data processing jobs
"""

        super().__init__(
            provider=provider,
            model=MODEL,
            system=system,
            tools=tools,
            tool_handlers=tool_handlers,
            max_tokens=max_tokens,
            max_rounds=max_rounds,
            **kwargs,
        )

        self._hook_delegate = None
        self.subagent_runner = SubagentRunner(provider, MODEL)
        self.task_manager = TaskManager(TASKS_DIR)
        self.background_manager = BackgroundManager()
        self.message_bus = MessageBus(INBOX_DIR)
        self.teammate_manager = TeammateManager(TEAM_DIR)
        self.plan_gate = PlanGate()

        # Initialize monitoring bridge (if event_bus is available)
        self._monitoring_bridge: CompositeMonitoringBridge | None = None
        try:
            # Generate a dialog_id based on session or use default
            dialog_id = kwargs.get("dialog_id", "sfull-default")
            self._monitoring_bridge = CompositeMonitoringBridge(
                dialog_id=dialog_id,
                agent_name="SFullAgent",
                event_bus=event_bus
            )
            self._monitoring_bridge.initialize()
            # Set monitoring bridge as hook delegate
            self.set_hook_delegate(self._monitoring_bridge)
            logger.info(f"[SFullAgent] Monitoring bridge initialized for dialog: {dialog_id}")
        except Exception as e:
            logger.warning(f"[SFullAgent] Failed to initialize monitoring bridge: {e}")

    def set_hook_delegate(self, delegate: Any) -> None:
        """Set external hook dispatcher for state management integration."""
        self._hook_delegate = delegate
        super().set_hook_delegate(delegate)

    def on_hook(self, hook: Any, **payload: Any) -> None:
        """Route hooks to delegate if set."""
        if self._hook_delegate is not None:
            self._hook_delegate.on_hook(hook, **payload)

    def get_monitoring_bridge(self) -> CompositeMonitoringBridge | None:
        """Get the monitoring bridge instance."""
        return self._monitoring_bridge

    def _run_bash_with_monitoring(self, command: str) -> str:
        """Run bash command with monitoring integration."""
        logger.info(f"[_run_bash_with_monitoring] Called with command: {command[:50]}...")

        dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
        if any(d in command for d in dangerous):
            return "Error: Dangerous command blocked"

        # Get monitoring bridge from context or instance
        bridge = None
        try:
            from agents.session.runtime_context import get_current_monitoring_bridge
            bridge = get_current_monitoring_bridge()
            logger.info(f"[_run_bash_with_monitoring] Got bridge from context: {bridge}")
        except Exception as e:
            logger.warning(f"[_run_bash_with_monitoring] Failed to get bridge from context: {e}")
            # Fallback to instance bridge
            bridge = self._monitoring_bridge
            logger.info(f"[_run_bash_with_monitoring] Using instance bridge: {bridge}")

        task_id = f"bash_{int(time.time() * 1000)}"
        bg_bridge = None

        # Create BackgroundTaskBridge
        if bridge:
            try:
                bg_bridge = bridge.create_background_task_bridge(task_id, command)
                logger.info(f"[_run_bash_with_monitoring] Created background task bridge: {task_id}")
            except Exception as e:
                logger.warning(f"[_run_bash_with_monitoring] Failed to create bridge: {e}")
                bg_bridge = None
        else:
            logger.warning("[_run_bash_with_monitoring] No monitoring bridge available")

        started_at = datetime.now()

        try:
            # Execute command
            r = subprocess.run(command, shell=True, cwd=WORKDIR,
                               capture_output=True, text=True, timeout=120)
            out = ((r.stdout or "") + (r.stderr or "")).strip()
            result = out[:50000] if out else "(no output)"

            # Send completion event
            if bg_bridge:
                try:
                    duration_ms = int((datetime.now() - started_at).total_seconds() * 1000)
                    from agents.monitoring.domain.event import EventType, EventPriority
                    from agents.monitoring.domain.payloads import BgTaskCompletedWithBridgePayload
                    payload = BgTaskCompletedWithBridgePayload(
                        task_id=task_id,
                        exit_code=r.returncode,
                        duration_ms=duration_ms,
                        output_lines=len(out.splitlines()),
                        bridge_id=str(bg_bridge.get_bridge_id())
                    )
                    bg_bridge._emit(
                        EventType.BG_TASK_COMPLETED,
                        payload=payload.model_dump(),
                        priority=EventPriority.HIGH
                    )
                    logger.info(f"[_run_bash_with_monitoring] Emitted BG_TASK_COMPLETED: {task_id}")
                except Exception as e:
                    logger.debug(f"[_run_bash_with_monitoring] Failed to emit completed event: {e}")

            return result
        except subprocess.TimeoutExpired:
            error_msg = "Error: Timeout (120s)"
            if bg_bridge:
                try:
                    from agents.monitoring.domain.event import EventType, EventPriority
                    from agents.monitoring.domain.payloads import BgTaskFailedWithExitCodePayload
                    payload = BgTaskFailedWithExitCodePayload(
                        task_id=task_id,
                        error=error_msg,
                        exit_code=-1,
                        bridge_id=str(bg_bridge.get_bridge_id())
                    )
                    bg_bridge._emit(
                        EventType.BG_TASK_FAILED,
                        payload=payload.model_dump(),
                        priority=EventPriority.CRITICAL
                    )
                except Exception:
                    pass
            return error_msg
        except Exception as e:
            error_msg = f"Error: {e}"
            if bg_bridge:
                try:
                    from agents.monitoring.domain.event import EventType, EventPriority
                    from agents.monitoring.domain.payloads import BgTaskFailedWithExitCodePayload
                    payload = BgTaskFailedWithExitCodePayload(
                        task_id=task_id,
                        error=str(e),
                        bridge_id=str(bg_bridge.get_bridge_id())
                    )
                    bg_bridge._emit(
                        EventType.BG_TASK_FAILED,
                        payload=payload.model_dump(),
                        priority=EventPriority.CRITICAL
                    )
                except Exception:
                    pass
            return error_msg


# Backward compatibility: Re-export from new modular structure
# These imports allow existing code to continue working during migration
def _warn_deprecation(old_name: str, new_module: str):
    """Emit deprecation warning for moved classes."""
    import warnings
    warnings.warn(
        f"{old_name} from s_full.py is deprecated. "
        f"Import from {new_module} instead.",
        DeprecationWarning,
        stacklevel=3
    )

# Re-export manager classes for backward compatibility
try:
    from ..plugins.todo import TodoManager as _NewTodoManager
    TodoManager = _NewTodoManager
except ImportError:
    pass  # Keep existing definition

try:
    from ..plugins.task import TaskManager as _NewTaskManager
    TaskManager = _NewTaskManager
except ImportError:
    pass  # Keep existing definition

try:
    from ..plugins.background import BackgroundManager as _NewBackgroundManager
    BackgroundManager = _NewBackgroundManager
except ImportError:
    pass  # Keep existing definition

try:
    from ..plugins.subagent import SubagentRunner as _NewSubagentRunner
    SubagentRunner = _NewSubagentRunner
except ImportError:
    pass  # Keep existing definition

try:
    from ..plugins.team import MessageBus as _NewMessageBus, TeammateManager as _NewTeammateManager
    MessageBus = _NewMessageBus
    TeammateManager = _NewTeammateManager
except ImportError:
    pass  # Keep existing definitions

try:
    from ..plugins.plan import PlanGate as _NewPlanGate
    PlanGate = _NewPlanGate
except ImportError:
    pass  # Keep existing definition

# Re-export agent classes with deprecation warnings
try:
    from ..agents import FullAgent, SFullAgent as _NewSFullAgent
    # SFullAgent is already defined above, but ensure it matches
    SFullAgent = FullAgent
except ImportError:
    pass  # Keep existing definition

# Global instance
AGENT_LOOP = SFullAgent()


def agent_loop(messages: list) -> None:
    """Run agent loop (sync wrapper)."""
    import asyncio
    asyncio.run(AGENT_LOOP.arun(messages))


async def async_agent_loop(messages: list) -> str:
    """Run agent loop asynchronously."""
    return await AGENT_LOOP.arun(messages)


if __name__ == "__main__":
    import asyncio

    async def main():
        history = []
        print("SFull Agent - Full capability agent")
        print("Commands: /compact, /tasks, /team, /inbox, q/exit to quit")
        print("-" * 50)

        while True:
            try:
                query = input("\033[36magent >> \033[0m")
            except (EOFError, KeyboardInterrupt):
                break

            if query.strip().lower() in ("q", "exit"):
                break
            if not query.strip():
                continue

            # REPL commands
            if query.strip() == "/compact":
                print("Context compaction triggered")
                continue
            if query.strip() == "/tasks":
                tasks = AGENT_LOOP.task_manager.list()
                print(f"Tasks: {len(tasks)}")
                for t in tasks[:5]:
                    print(f"  - {t['id']}: {t['title']} ({t['status']})")
                continue
            if query.strip() == "/team":
                teammates = AGENT_LOOP.teammate_manager.list()
                print(f"Teammates: {len(teammates)}")
                for tm in teammates:
                    print(f"  - {tm['name']} ({tm['status']})")
                continue
            if query.strip() == "/inbox":
                msgs = AGENT_LOOP.message_bus.read("default")
                print(f"Inbox: {len(msgs)} messages")
                for m in msgs[-3:]:
                    print(f"  - {m.get('from', '?')}: {m.get('content', '')[:50]}")
                continue

            history.append({"role": "user", "content": query})
            result = await AGENT_LOOP.arun(history)
            logger.info(f"Result: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
            print()

    asyncio.run(main())
