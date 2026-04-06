"""Deep Message Handler Mixin - 消息处理功能

从 deep_legacy.py 提取的 send_message 逻辑。
"""

import os
from typing import AsyncIterator, Any, Optional
from loguru import logger

from backend.domain.models.shared import AgentEvent
from backend.domain.models.events.event_models import UserMessageModel
from backend.infrastructure.llm_adapter import LLMResponseAdapterFactory
from pydantic import BaseModel


class DeepMessageHandlerMixin:
    """消息处理 Mixin

    注意：此 Mixin 依赖以下其他 Mixin 提供的属性/方法：
    - DeepModelSwitcherMixin: _ensure_agent_for_dialog, session_manager
    - DeepInitializerMixin: _merge_system_messages, _init_unified_loggers
    - UnifiedLoggingMixin: _fire_log_msg, _fire_log_update, _fire_log_tool_result
    - DeepCheckpointMixin: _get_checkpoint_snapshot
    """

    # 来自其他 Mixin 的属性
    _agent: Any
    _config: Any
    _model_name: Optional[str]
    _checkpointer: Any
    _adapter_factory: LLMResponseAdapterFactory
    _session_mgr: Any  # from DeepModelSwitcherMixin

    # 来自其他 Mixin 的方法（运行时注入）
    _ensure_agent_for_dialog: Any
    _merge_system_messages: Any
    _fire_log_msg: Any
    _fire_log_update: Any
    _fire_log_tool_result: Any
    _get_checkpoint_snapshot: Any
    session_manager: Any
    is_stop_requested: Any
    clear_stop_request: Any

    async def send_message(
        self,
        dialog_id: str,
        message: str,
        stream: bool = True,
        message_id: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]:
        """发送消息，返回流式事件"""
        if self._agent is None:
            raise RuntimeError("DeepAgentRuntime not initialized")

        await self._ensure_agent_for_dialog(dialog_id)

        session_mgr = self.session_manager
        if session_mgr is not None:
            session = await session_mgr.get_session(dialog_id)
            if session is None:
                await session_mgr.create_session(dialog_id, title=message[:50])
            history_messages = await session_mgr.get_messages(dialog_id)
            messages = []
            for msg in history_messages:
                if hasattr(msg, 'model_dump'):
                    messages.append(msg.model_dump())
                elif hasattr(msg, 'content'):
                    messages.append({"role": getattr(msg, 'type', 'unknown'), "content": msg.content})
                else:
                    messages.append(msg)
            ai_message_id = message_id or f"msg_{id(message)}"
            await session_mgr.start_ai_response(dialog_id, ai_message_id)
        else:
            user_msg = UserMessageModel(role="user", content=message)
            messages = [user_msg.model_dump() if isinstance(user_msg, BaseModel) else {"role": "user", "content": message}]
            ai_message_id = message_id or f"msg_{id(message)}"

        messages = self._merge_system_messages(messages)
        recursion_limit = int(os.getenv("AGENT_RECURSION_LIMIT", "100").strip())
        config = {"configurable": {"thread_id": dialog_id}, "recursion_limit": recursion_limit}

        self._fire_log_msg("debug", f"User message: {message[:200]}", dialog_id)

        accumulated_content = ""
        accumulated_reasoning = ""
        actual_model_name = None

        # 跟踪工具调用，用于关联 tool_call 和 tool_result
        pending_tool_calls: dict[str, dict[str, Any]] = {}

        try:
            async for raw_event in self._agent.astream(
                {"messages": messages}, config, stream_mode=["messages"]
            ):
                # 检查是否请求停止
                if self.is_stop_requested(dialog_id):
                    logger.info(f"[DeepAgentRuntime] Stopping dialog {dialog_id} as requested")
                    self.clear_stop_request(dialog_id)
                    yield AgentEvent(type="error", data="Agent stopped by user")
                    return

                delta_content = ""
                delta_reasoning = ""
                event_metadata = None

                if isinstance(raw_event, tuple) and len(raw_event) >= 2:
                    msg_chunk = raw_event[1]
                    if isinstance(msg_chunk, tuple):
                        event_metadata = msg_chunk[1] if len(msg_chunk) > 1 else None
                        msg_chunk = msg_chunk[0]

                    if actual_model_name is None and event_metadata:
                        actual_model_name = event_metadata.get('ls_model_name')

                    if getattr(msg_chunk, 'type', None) == 'tool':
                        tool_call_id = getattr(msg_chunk, 'tool_call_id', 'unknown')
                        tool_content = getattr(msg_chunk, 'content', '')

                        # 从 pending_tool_calls 获取工具名和参数
                        pending = pending_tool_calls.pop(tool_call_id, None)
                        if pending:
                            tool_name = pending.get('name', 'unknown')
                            tool_args = pending.get('args', {})
                        else:
                            tool_name = getattr(msg_chunk, 'name', 'unknown')
                            tool_args = {}

                        result_data = {"tool_name": tool_name, "tool_call_id": tool_call_id, "result": str(tool_content)}
                        yield AgentEvent(
                            type="tool_result",
                            data=result_data,
                            metadata={"tool_call_id": tool_call_id}
                        )

                        # 记录完整的工具执行结果到 jsonl
                        self._fire_log_tool_result(
                            tool_name=tool_name,
                            arguments=tool_args,
                            result=str(tool_content),
                            dialog_id=dialog_id
                        )
                        continue

                    if getattr(msg_chunk, 'type', None) in ('ai', 'assistant'):
                        tool_calls = getattr(msg_chunk, 'tool_calls', None) or []
                        for tc in tool_calls:
                            tc_id = tc.get('id', 'call_0')
                            tc_name = tc.get('name', 'unknown')
                            tc_args = tc.get('args', {})
                            if isinstance(tc_args, str):
                                try:
                                    import json
                                    tc_args = json.loads(tc_args)
                                except Exception:
                                    tc_args = {"raw": tc_args}

                            # 存储到 pending_tool_calls 用于后续关联 tool_result
                            pending_tool_calls[tc_id] = {"name": tc_name, "args": tc_args}

                            yield AgentEvent(
                                type="tool_call",
                                data={"message_id": message_id or "unknown", "tool_call": {"id": tc_id, "name": tc_name, "arguments": tc_args, "status": "pending"}},
                            )
                            # 记录工具调用（pending 状态）到 jsonl
                            self._fire_log_tool_result(tc_name, tc_args, {"status": "pending", "tool_call_id": tc_id}, dialog_id)

                    if hasattr(msg_chunk, 'content') and msg_chunk.content:
                        content = msg_chunk.content
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get('type') == 'text':
                                    delta_content += block.get('text', '')
                                elif isinstance(block, str):
                                    delta_content += block
                        else:
                            delta_content = str(content)

                    if hasattr(msg_chunk, 'additional_kwargs'):
                        reasoning = msg_chunk.additional_kwargs.get('reasoning_content', '')
                        if reasoning:
                            delta_reasoning = str(reasoning)

                if session_mgr is not None:
                    if delta_content:
                        await session_mgr.emit_delta(dialog_id, delta_content, ai_message_id)
                    if delta_reasoning:
                        await session_mgr.emit_reasoning_delta(dialog_id, delta_reasoning, ai_message_id)

                if delta_content:
                    accumulated_content += delta_content
                    yield AgentEvent(type="text_delta", data=delta_content, metadata={"accumulated_length": len(accumulated_content)})

                if delta_reasoning:
                    accumulated_reasoning += delta_reasoning
                    yield AgentEvent(type="reasoning_delta", data=delta_reasoning, metadata={"accumulated_length": len(accumulated_reasoning)})

            if session_mgr is not None and accumulated_content:
                session = await session_mgr.get_session(dialog_id)
                if session and session.status.value not in ("completed", "closed"):
                    effective_model = actual_model_name or self._model_name or "unknown"
                    completion_metadata = {"model": effective_model, "provider": self._adapter_factory.detect_provider(effective_model) or "unknown"}
                    if accumulated_reasoning:
                        completion_metadata["reasoning_content"] = accumulated_reasoning
                    await session_mgr.complete_ai_response(dialog_id, ai_message_id, accumulated_content, metadata=completion_metadata)
                    self._fire_log_update("info", f"AI response completed: dialog_id={dialog_id}, content_len={len(accumulated_content)}", dialog_id)

                    checkpoint_data = self._get_checkpoint_snapshot(dialog_id)
                    snapshot_path = session_mgr.save_checkpoint_snapshot(checkpoint_data)
                    if snapshot_path:
                        self._fire_log_update("debug", f"Checkpoint snapshot saved: {snapshot_path}", dialog_id)

            # 正常完成，清除停止请求
            self.clear_stop_request(dialog_id)

            if accumulated_content:
                effective_model = actual_model_name or self._model_name or "unknown"
                completion_metadata = {"reasoning_content": accumulated_reasoning, "model": effective_model, "provider": self._adapter_factory.detect_provider(effective_model) or "unknown", "content_length": len(accumulated_content)}
                yield AgentEvent(type="text_complete", data=accumulated_content, metadata=completion_metadata)

        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            logger.exception(f"[DeepAgentRuntime] Error in send_message: {e}")
            self._fire_log_msg("error", f"Error: {error_detail}", dialog_id)

            if accumulated_content and session_mgr is not None:
                logger.warning(f"[DeepAgentRuntime] Saving partial content: {len(accumulated_content)} chars")
                try:
                    effective_model = actual_model_name or self._model_name or "unknown"
                    completion_metadata = {"model": effective_model, "provider": self._adapter_factory.detect_provider(effective_model) or "unknown", "error_interrupted": True, "error_type": type(e).__name__}
                    if accumulated_reasoning:
                        completion_metadata["reasoning_content"] = accumulated_reasoning
                    await session_mgr.complete_ai_response(dialog_id, ai_message_id, accumulated_content, completion_metadata)
                    yield AgentEvent(type="text_complete", data=accumulated_content, metadata=completion_metadata)
                except Exception as save_error:
                    logger.error(f"[DeepAgentRuntime] Failed to save partial content: {save_error}")

            yield AgentEvent(type="error", data=str(e))
