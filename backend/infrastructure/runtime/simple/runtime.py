"""Simple Runtime - 基于 SimpleAgent 的完整功能 Runtime 实现

通过继承 ManagerAwareRuntime 获得完整 Manager 功能。
"""

import json
import os
from collections.abc import AsyncIterator, Callable
from typing import Any

from loguru import logger

from backend.domain.models import ToolCall
from backend.domain.models.dialog import DialogSessionManager
from backend.domain.models.events import AgentRoundsLimitReached, ErrorOccurred
from backend.domain.models.events.agent import AgentEvent
from backend.domain.models.shared.config import EngineConfig
from backend.domain.models.shared.types import MessageDict, ToolCallDict
from backend.infrastructure.plugins import CompactPlugin, PluginManager
from backend.infrastructure.runtime.base.manager import ManagerAwareRuntime
from backend.infrastructure.tools import WorkspaceOps


class SimpleRuntime(ManagerAwareRuntime):
    """Simple Runtime - 继承 ManagerAwareRuntime 获得完整 Manager 功能"""

    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self._plugin_mgr = PluginManager(self._event_bus)
        logger.debug(f"[{self.__class__.__name__}] Created: {agent_id}")

    @property
    def agent_type(self) -> str:
        return "simple"

    @property
    def session_manager(self) -> DialogSessionManager | None:
        """获取 SessionManager 实例"""
        return self._session_mgr

    async def _do_initialize(self) -> None:
        """初始化 SimpleRuntime 特定组件"""
        config = self._config
        if config is None:
            raise ValueError("Config not set")

        if isinstance(config, dict):
            config = EngineConfig.model_validate(config)

        await self._initialize_managers(config)

        self._plugin_mgr.register(CompactPlugin)

        for tool in self._plugin_mgr.get_all_tools():
            spec = getattr(tool, "__tool_spec__", None)
            if spec is None:
                continue
            if hasattr(spec, "model_dump"):
                spec = spec.model_dump()
            self._tool_mgr.register(
                name=spec.get("name", getattr(tool, "__name__", "")),
                handler=tool,
                description=spec.get("description", ""),
                parameters=spec.get("parameters", {}),
            )

        await self._load_state()
        self._skill_mgr.load_builtin_skills()
        self._emit_system_started()

    async def _do_shutdown(self) -> None:
        """清理资源"""
        await self._save_state()
        self._emit_system_stopped()
        self._shutdown_event_bus()

    async def _load_state(self) -> None:
        """加载状态（可扩展）"""
        pass

    async def _save_state(self) -> None:
        """保存状态（可扩展）"""
        pass

    def _emit_system_started(self) -> None:
        """发射系统启动事件"""
        from backend.domain.models.events import SystemStarted

        self._event_bus.emit(SystemStarted())

    def _emit_system_stopped(self) -> None:
        """发射系统停止事件"""
        from backend.domain.models.events import SystemStopped

        self._event_bus.emit(SystemStopped())

    @staticmethod
    def _convert_messages_to_dict(messages: list) -> list[MessageDict]:
        """将消息列表转换为字典格式（用于 LiteLLM）。"""
        from langchain_core.messages import (
            AIMessage,
            BaseMessage,
            HumanMessage,
            SystemMessage,
            ToolMessage,
        )

        result = []
        for msg in messages:
            if isinstance(msg, dict):
                result.append(msg)
            elif isinstance(msg, BaseMessage):
                # LangChain 消息对象转换为字典
                if isinstance(msg, HumanMessage):
                    result.append(MessageDict(role="user", content=str(msg.content)))
                elif isinstance(msg, AIMessage):
                    item = MessageDict(
                        role="assistant", content=str(msg.content) if msg.content else ""
                    )
                    if msg.tool_calls:
                        item["tool_calls"] = msg.tool_calls
                    result.append(item)
                elif isinstance(msg, ToolMessage):
                    result.append(
                        MessageDict(
                            role="tool", content=str(msg.content), tool_call_id=msg.tool_call_id
                        )
                    )
                elif isinstance(msg, SystemMessage):
                    result.append(MessageDict(role="system", content=str(msg.content)))
                else:
                    # 默认处理
                    result.append(MessageDict(role="user", content=str(msg.content)))
            else:
                # 其他类型，尝试获取属性
                role = getattr(msg, "type", "user")
                if role == "human":
                    role = "user"
                elif role == "ai":
                    role = "assistant"
                result.append(MessageDict(role=role, content=str(getattr(msg, "content", ""))))
        return result

    def _shutdown_event_bus(self) -> None:
        """关闭事件总线"""
        self._event_bus.shutdown()

    async def send_message(  # type: ignore[override]
        self,
        dialog_id: str,
        message: str,
        stream: bool = True,
        message_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """发送消息，返回流式事件（使用 SessionManager 管理状态）"""

        # 使用 SessionManager 管理对话状态
        if self._session_mgr is not None:
            # 确保会话存在
            session = await self._session_mgr.get_session(dialog_id)
            if session is None:
                await self._session_mgr.create_session(dialog_id, title="New Dialog")

            # 添加用户消息
            await self._session_mgr.add_user_message(dialog_id, message)
            raw_messages = await self._session_mgr.get_messages_for_llm(dialog_id)
            messages = self._convert_messages_to_dict(raw_messages)
        else:
            # 回退到旧方式
            await self._dialog_mgr.add_user_message(dialog_id, message)
            raw_messages = self._dialog_mgr.get_messages_for_llm(dialog_id)
            messages = self._convert_messages_to_dict(raw_messages)

        logger.info(f"[{self.__class__.__name__}] User message: dialog={dialog_id}")

        provider = self._provider_mgr.default
        if not provider:
            yield AgentEvent(type="error", data="Error: No provider available")
            return

        system_prompt = self._build_system_prompt()
        if system_prompt:
            messages.insert(0, MessageDict(role="system", content=system_prompt))

        tools = self._tool_mgr.get_schemas()

        try:
            _max_rounds_env = os.getenv("MAX_AGENT_ROUNDS", "").strip()
            max_rounds = int(_max_rounds_env) if _max_rounds_env.isdigit() else None

            _round = 0
            assistant_text = ""

            while max_rounds is None or _round < max_rounds:
                _round += 1
                full_response: list[str] = []
                tool_calls_in_round: list[dict] = []

                async for chunk in provider.chat_stream(
                    messages=messages, tools=tools if tools else None
                ):
                    if chunk.is_content:
                        full_response.append(chunk.content)
                        if stream:
                            yield AgentEvent(
                                type="text_delta", data=chunk.content, metadata={"round": _round}
                            )
                    elif chunk.is_tool_call and chunk.tool_call is not None:
                        tool_calls_in_round.append(dict(chunk.tool_call))

                assistant_text = "".join(full_response)

                if not tool_calls_in_round:
                    break

                if max_rounds is not None and _round >= max_rounds:
                    self._event_bus.emit(
                        AgentRoundsLimitReached(dialog_id=dialog_id, rounds=_round)
                    )
                    notice = f"\n\n⚠️ Agent 已达到最大轮次限制（{max_rounds} 轮），任务中止。"
                    if stream:
                        yield AgentEvent(type="text_delta", data=notice)
                    assistant_text += notice
                    break

                tool_call_dicts: list[ToolCallDict] = [
                    {
                        "id": tc.get("id", f"call_{i}"),
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"])
                            if isinstance(tc["arguments"], dict)
                            else tc["arguments"],
                        },
                    }
                    for i, tc in enumerate(tool_calls_in_round)
                ]
                messages.append(
                    MessageDict(
                        role="assistant",
                        content=assistant_text or "",
                        tool_calls=tool_call_dicts,
                    )
                )

                for tc in tool_calls_in_round:
                    tool_call = ToolCall.create(name=tc["name"], arguments=tc["arguments"])

                    yield AgentEvent(
                        type="tool_call",
                        data={
                            "message_id": message_id or "unknown",
                            "tool_call": {
                                "id": tc.get("id", "call_0"),
                                "name": tc["name"],
                                "arguments": tc["arguments"]
                                if isinstance(tc["arguments"], dict)
                                else {},
                                "status": "pending",
                            },
                        },
                    )

                    result = await self._tool_mgr.execute(dialog_id, tool_call)

                    messages.append(
                        MessageDict(
                            role="tool",
                            content=str(result),
                            tool_call_id=tc.get("id", "call_0"),
                        )
                    )

                    yield AgentEvent(
                        type="tool_result",
                        data={
                            "tool_name": tc["name"],
                            "tool_call_id": tc.get("id", "call_0"),
                            "result": str(result),
                        },
                        metadata={"tool_call_id": tc.get("id", "call_0")},
                    )

            # 使用 SessionManager 保存完整 AI 回复
            logger.info(
                f"[SimpleRuntime] Saving AI response for {dialog_id}, text_len={len(assistant_text)}, _session_mgr={self._session_mgr is not None}"
            )
            if self._session_mgr is not None:
                try:
                    await self._session_mgr.complete_ai_response(
                        dialog_id,
                        message_id or "msg_unknown",
                        assistant_text,
                        metadata={"rounds": _round},
                    )
                    logger.info(f"[SimpleRuntime] AI response saved successfully for {dialog_id}")
                except Exception as e:
                    logger.error(f"[SimpleRuntime] Failed to save AI response for {dialog_id}: {e}")
            else:
                await self._dialog_mgr.add_assistant_message(
                    dialog_id, assistant_text, message_id=message_id
                )
            yield AgentEvent(type="message_complete", data=assistant_text)

        except Exception as e:
            logger.exception(f"[{self.__class__.__name__}] Error: {e}")
            self._event_bus.emit(
                ErrorOccurred(
                    error_type=type(e).__name__, error_message=str(e), dialog_id=dialog_id
                )
            )
            yield AgentEvent(type="error", data=str(e))

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        parts = ["You are a helpful AI assistant."]

        memory = self._memory_mgr.load_memory()
        if memory and memory.strip() != "# Agent Memory":
            parts.append("\n# Long-term Memory\n" + memory)

        skill_prompts = []
        for skill in self._skill_mgr.list_skills():
            prompt = self._skill_mgr.get_skill_prompt(skill.id)
            if prompt:
                skill_prompts.append(f"[{skill.name}]\n{prompt}")

        if skill_prompts:
            parts.append("\nActive skills:")
            parts.append("\n\n".join(skill_prompts))

        plugin_prompt = self._plugin_mgr.get_combined_system_prompt()
        if plugin_prompt:
            parts.append(plugin_prompt)

        return "\n".join(parts)

    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str,
        parameters_schema: dict[str, Any] | None = None,
    ) -> None:
        """注册工具（注册到 ToolManager）"""
        from backend.domain.models.shared.types import JSONSchema
        from backend.infrastructure.runtime.base.runtime import ToolCache

        json_schema: JSONSchema | None = None
        if parameters_schema is not None:
            if isinstance(parameters_schema, dict):
                json_schema = JSONSchema(**parameters_schema)
            else:
                json_schema = parameters_schema  # type: ignore[assignment]

        self._tool_mgr.register(
            name=name, handler=handler, description=description, parameters=json_schema
        )

        self._tools[name] = ToolCache(
            handler=handler, description=description, parameters_schema=parameters_schema or {}
        )

        logger.debug(f"[{self.__class__.__name__}] Registered tool: {name}")

    def unregister_tool(self, name: str) -> None:
        """注销工具"""
        self._tool_mgr.unregister(name)
        self._tools.pop(name, None)
        logger.debug(f"[{self.__class__.__name__}] Unregistered tool: {name}")

    async def stop(self, dialog_id: str | None = None) -> None:
        """停止 Agent"""
        logger.info(f"[{self.__class__.__name__}] Stopped: {self._agent_id}")

    def get_skill_edit_proposals(self, dialog_id: str | None = None) -> list[dict]:
        """获取待处理的 Skill 编辑提案"""
        from backend.hitl import is_skill_edit_hitl_enabled, skill_edit_hitl_store

        if not is_skill_edit_hitl_enabled():
            return []
        return skill_edit_hitl_store.list_pending(dialog_id)

    def decide_skill_edit(
        self, approval_id: str, decision: str, edited_content: str | None = None
    ) -> Any:
        """处理 Skill 编辑审核决定"""
        from backend.domain.models.api import DecisionResult
        from backend.hitl import is_skill_edit_hitl_enabled, skill_edit_hitl_store

        if not is_skill_edit_hitl_enabled():
            return DecisionResult(success=False, message="HITL disabled")
        return skill_edit_hitl_store.decide(approval_id, decision, edited_content)

    def get_todos(self, dialog_id: str) -> Any:
        """获取对话的 Todo 列表"""
        from backend.domain.models.api import TodoStateDTO
        from backend.hitl import is_todo_hook_enabled, todo_store

        if not is_todo_hook_enabled():
            return TodoStateDTO(dialog_id=dialog_id, items=[], rounds_since_todo=0, updated_at=0.0)
        return todo_store.get_todos(dialog_id)

    def update_todos(self, dialog_id: str, items: list[dict]) -> tuple[bool, str]:
        """更新对话的 Todo 列表"""
        from backend.hitl import is_todo_hook_enabled, todo_store

        if not is_todo_hook_enabled():
            return False, "Todo HITL disabled"
        return todo_store.update_todos(dialog_id, items)

    def register_hitl_broadcaster(self, broadcaster: Callable[[dict[str, Any]], Any]) -> None:
        """注册 HITL 广播器"""
        from backend.hitl import (
            is_skill_edit_hitl_enabled,
            is_todo_hook_enabled,
            skill_edit_hitl_store,
            todo_store,
        )

        if is_skill_edit_hitl_enabled():
            skill_edit_hitl_store.register_broadcaster(broadcaster)
        if is_todo_hook_enabled():
            todo_store.register_broadcaster(broadcaster)

    def setup_workspace_tools(self, workdir: Any) -> None:
        """快速设置工作区工具"""
        from pathlib import Path

        workspace = WorkspaceOps(Path(workdir))

        for tool_fn in workspace.get_tools():
            spec = getattr(tool_fn, "__tool_spec__", {})
            self.register_tool(
                name=spec.get("name", getattr(tool_fn, "__name__", "")),
                handler=tool_fn,
                description=spec.get("description", ""),
                parameters_schema=spec.get("parameters", {}),
            )

        logger.info(f"[{self.__class__.__name__}] Setup workspace tools from {workdir}")

    @property
    def plugin_manager(self) -> PluginManager:
        """插件管理器（高级用例）"""
        return self._plugin_mgr


__all__ = ["SimpleRuntime"]
