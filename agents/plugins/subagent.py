"""Subagent Plugin - Subagent spawning for task decomposition."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any, Callable

from ..base import tool
from .base import AgentPlugin

if TYPE_CHECKING:
    from ..agent.base_agent_loop import BaseAgentLoop


class SubagentRunner:
    """Run subagents for task decomposition."""

    def __init__(self, provider, model: str):
        self.provider = provider
        self.model = model

    async def run(self, prompt: str, agent_type: str = "Explore", name: str = "", dialog_id: str = None) -> str:
        """Run a subagent with limited tools."""
        from ..session.runtime_context import get_current_dialog_id

        prompt = prompt or ""
        agent_type = agent_type or "Explore"
        name = name or ""

        subagent_id = name or f"Subagent_{agent_type}_{id(self) % 10000}"
        agent_name = f"Subagent:{agent_type}:{subagent_id}"

        try:
            from ..monitoring.domain import MonitoringEvent, EventType, EventPriority
            from ..monitoring.services import event_bus
            from ..monitoring.domain.payloads import SubagentStartedPayload, SubagentCompletedPayload, SubagentFailedPayload

            if dialog_id is None:
                dialog_id = get_current_dialog_id() or "system"

            # Emit SUBAGENT_STARTED
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
            event_bus.emit_sync(event)
            monitoring_available = True
        except ImportError:
            monitoring_available = False

        # Subagent tools (limited set)
        sub_tools = [
            {"type": "function", "function": {"name": "bash", "description": "Run command.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
            {"type": "function", "function": {"name": "read_file", "description": "Read file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
        ]

        if agent_type != "Explore":
            sub_tools.extend([
                {"type": "function", "function": {"name": "write_file", "description": "Write file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
                {"type": "function", "function": {"name": "edit_file", "description": "Edit file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}}},
            ])

        # Simple handlers
        def run_bash(command: str) -> str:
            import subprocess
            try:
                r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
                return (r.stdout or "") + (r.stderr or "")
            except Exception as e:
                return str(e)

        def run_read(path: str) -> str:
            from pathlib import Path
            try:
                return Path(path).read_text(encoding="utf-8")
            except Exception as e:
                return str(e)

        def run_write(path: str, content: str) -> str:
            from pathlib import Path
            try:
                Path(path).write_text(content, encoding="utf-8")
                return "written"
            except Exception as e:
                return str(e)

        def run_edit(path: str, old_text: str, new_text: str) -> str:
            from pathlib import Path
            try:
                p = Path(path)
                content = p.read_text(encoding="utf-8")
                p.write_text(content.replace(old_text, new_text), encoding="utf-8")
                return "edited"
            except Exception as e:
                return str(e)

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

                if tool_calls:
                    sub_msgs.append({"role": "assistant", "content": content or None, "tool_calls": tool_calls})
                    for tc in tool_calls:
                        fn_name = tc["function"]["name"]
                        try:
                            args = json.loads(tc["function"]["arguments"])
                        except Exception:
                            args = {}
                        result = sub_handlers.get(fn_name, lambda **_: "Unknown tool")(**args)
                        sub_msgs.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": str(result)
                        })
                else:
                    final_content = content
                    break

            if monitoring_available:
                completed_payload = SubagentCompletedPayload(
                    subagent_name=subagent_id,
                    subagent_type=agent_type,
                    result_preview=final_content[:500] if final_content else ""
                )
                event = MonitoringEvent(
                    type=EventType.SUBAGENT_COMPLETED,
                    dialog_id=dialog_id,
                    source=agent_name,
                    context_id=str(uuid.uuid4()),
                    priority=EventPriority.HIGH,
                    payload=completed_payload.model_dump()
                )
                event_bus.emit_sync(event)

            return final_content

        except Exception as e:
            if monitoring_available:
                failed_payload = SubagentFailedPayload(
                    subagent_name=subagent_id,
                    subagent_type=agent_type,
                    error=str(e)[:200]
                )
                event = MonitoringEvent(
                    type=EventType.SUBAGENT_FAILED,
                    dialog_id=dialog_id,
                    source=agent_name,
                    context_id=str(uuid.uuid4()),
                    priority=EventPriority.CRITICAL,
                    payload=failed_payload.model_dump()
                )
                event_bus.emit_sync(event)
            return f"Error: {e}"


class SubagentPlugin(AgentPlugin):
    """Plugin providing subagent spawning for task decomposition.

    Allows agents to spawn limited-capability subagents for specific tasks.
    Emits monitoring events for subagent lifecycle (SUBAGENT_*).
    """

    def __init__(self, provider=None, model: str = None):
        super().__init__()
        if provider is None:
            from ..providers import create_provider_from_env
            provider = create_provider_from_env()
        if model is None:
            model = provider.default_model if provider else "deepseek-chat"
        self._runner = SubagentRunner(provider, model)

    @property
    def name(self) -> str:
        return "subagent"

    def get_tools(self) -> list[Callable]:
        return [self._subagent]

    @tool(
        name="subagent",
        description="Spawn a subagent for task decomposition. agent_type: Explore|General|Code|Test|Review"
    )
    async def _subagent(self, prompt: str, agent_type: str = "Explore", name: str = "") -> str:
        """Spawn a subagent to handle a specific task.

        Args:
            prompt: The task description for the subagent.
            agent_type: Type of subagent (Explore, General, Code, Test, Review).
            name: Optional custom name for the subagent.

        Returns:
            The subagent's result as a string.
        """
        from ..session.runtime_context import get_current_dialog_id

        dialog_id = get_current_dialog_id()
        result = await self._runner.run(prompt, agent_type, name, dialog_id)
        return result
