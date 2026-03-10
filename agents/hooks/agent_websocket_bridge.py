"""
AgentWebSocketBridge - Agent 与 WebSocket 之间的桥接层

侵入性最小的设计：
1. 通过 BaseAgentLoop 的钩子函数捕获事件
2. 转换为 ChatEvent 并通过 WebSocket 广播
3. 不修改 Agent 内部逻辑，只在外层包装
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from loguru import logger

try:
    from ..models import ChatMessage, ChatEvent, ChatCompletionMessageToolCall
    from ..websocket.server import connection_manager
    from ..websocket.event_manager import event_manager
    from ..base.abstract import FullAgentHooks, HookName
    from ..utils.workspace_cleanup import clear_workspace_dir
except ImportError:
    from agents.models import ChatMessage, ChatEvent, ChatCompletionMessageToolCall
    from agents.websocket.server import connection_manager
    from agents.websocket.event_manager import event_manager
    from agents.base.abstract import FullAgentHooks, HookName
    from agents.utils.workspace_cleanup import clear_workspace_dir


@dataclass
class StreamingBuffer:
    """流式内容缓冲区，用于聚合分片内容"""
    content: str = ""
    reasoning_content: str = ""
    tool_calls: list = field(default_factory=list)
    hook_stats: dict = field(default_factory=dict)

    def reset(self):
        self.content = ""
        self.reasoning_content = ""
        self.tool_calls = []
        self.hook_stats = {
            "stream_total": 0,
            "content_chunks": 0,
            "reasoning_chunks": 0,
            "tool_chunks": 0,
            "done_chunks": 0,
            "error_chunks": 0,
            "tool_calls": [],
            "complete_payload": "",
            "errors": [],
            "after_run_rounds": 0,
        }

    def to_dict(self) -> dict:
        """转换为字典格式，用于序列化"""
        return {
            "content": self.content,
            "reasoning_content": self.reasoning_content,
            "tool_calls": self.tool_calls,
        }


class AgentWebSocketBridge(FullAgentHooks):
    """
    Agent 与 WebSocket 之间的桥接器

    使用方式:
        bridge = AgentWebSocketBridge(dialog_id="xxx", agent_name="TeamLeadAgent")
        agent = TeamLeadAgent(
            dialog_id=dialog_id,
            on_stream_token=bridge.on_stream_token,
            on_tool_call=bridge.on_tool_call,
            on_complete=bridge.on_complete,
            on_reasoning=bridge.on_reasoning,
            on_error=bridge.on_error,
        )
    """

    def __init__(self, dialog_id: str, agent_name: str = "TeamLeadAgent", enable_streaming: bool = True):
        self.dialog_id = dialog_id
        self.agent_name = agent_name
        self.enable_streaming = enable_streaming
        self.buffer = StreamingBuffer()
        self.buffer.reset()
        self._message_id = 0
        self._current_assistant_message: Optional[ChatMessage] = None
        # 保存事件循环引用，用于线程安全调度
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    def _get_next_message_id(self) -> str:
        """生成消息 ID"""
        self._message_id += 1
        return f"{self.dialog_id}_msg_{self._message_id}"

    async def _broadcast_event(self, event_type: str, data: dict):
        """广播事件到 WebSocket"""
        try:
            await connection_manager.broadcast({
                "type": f"agent:{event_type}",
                "dialog_id": self.dialog_id,
                "data": data,
            })
        except Exception as e:
            logger.error(f"[AgentBridge] Failed to broadcast event: {e}")

    def _safe_broadcast(self, event_type: str, data: dict):
        """线程安全地广播事件"""
        logger.debug(f"[AgentBridge] Broadcasting event: {event_type}, data keys: {list(data.keys())}")
        if self._loop and self._loop.is_running():
            # 在主事件循环中调度
            asyncio.run_coroutine_threadsafe(
                self._broadcast_event(event_type, data),
                self._loop
            )
        else:
            # 如果没有事件循环，尝试获取当前运行的循环或创建新循环
            try:
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        # 使用现有的运行中循环
                        asyncio.run_coroutine_threadsafe(
                            self._broadcast_event(event_type, data),
                            loop
                        )
                    else:
                        # 尝试直接运行
                        loop.run_until_complete(self._broadcast_event(event_type, data))
                except RuntimeError:
                    # 没有运行中的循环，创建新循环
                    new_loop = asyncio.new_event_loop()
                    try:
                        new_loop.run_until_complete(self._broadcast_event(event_type, data))
                    finally:
                        new_loop.close()
            except Exception as e:
                logger.warning(f"[AgentBridge] Could not broadcast event: {e}")

    def _create_assistant_message(self) -> ChatMessage:
        """创建助手消息"""
        msg = ChatMessage.assistant("")
        msg.id = self._get_next_message_id()
        return msg

    # ===== Hook Handlers =====

    def on_before_run(self, messages: list[dict[str, Any]]) -> None:
        _ = messages
        self.buffer.reset()
        # 重置当前助手消息，确保每轮对话只有一个 Agent 框
        self._current_assistant_message = None
        self._message_id = 0

    def on_stream_token(self, chunk: Any):
        """
        处理流式 token

        BaseAgentLoop 会在每个内容块到达时调用此钩子
        """
        if not self.enable_streaming:
            return

        try:
            # 创建或获取当前的助手消息
            if self._current_assistant_message is None:
                self._current_assistant_message = self._create_assistant_message()
                # 发送开始事件，包含 agent_name
                self._safe_broadcast("message_start", {
                    "message_id": self._current_assistant_message.id,
                    "role": "assistant",
                    "agent_name": self.agent_name,
                })

            # 根据 chunk 类型处理
            if hasattr(chunk, 'is_content') and chunk.is_content:
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                self.buffer.content += content
                self.buffer.hook_stats["stream_total"] += 1
                self.buffer.hook_stats["content_chunks"] += 1
                logger.debug(f"[AgentBridge] Content chunk received: {content[:50]}...")

                # 发送增量内容，包含 agent_name
                self._safe_broadcast("content_delta", {
                    "message_id": self._current_assistant_message.id,
                    "delta": content,
                    "content": self.buffer.content,
                    "agent_name": self.agent_name,
                })

            elif hasattr(chunk, 'is_reasoning') and chunk.is_reasoning:
                reasoning = chunk.reasoning_content if hasattr(chunk, 'reasoning_content') else str(chunk)
                self.buffer.reasoning_content += reasoning
                self.buffer.hook_stats["stream_total"] += 1
                self.buffer.hook_stats["reasoning_chunks"] += 1

                # 发送推理内容
                self._safe_broadcast("reasoning_delta", {
                    "message_id": self._current_assistant_message.id,
                    "delta": reasoning,
                    "reasoning_content": self.buffer.reasoning_content,
                })

            elif hasattr(chunk, 'is_tool_call') and chunk.is_tool_call:
                self.buffer.hook_stats["stream_total"] += 1
                self.buffer.hook_stats["tool_chunks"] += 1
            elif hasattr(chunk, 'is_done') and chunk.is_done:
                self.buffer.hook_stats["stream_total"] += 1
                self.buffer.hook_stats["done_chunks"] += 1
            elif hasattr(chunk, 'is_error') and chunk.is_error:
                self.buffer.hook_stats["stream_total"] += 1
                self.buffer.hook_stats["error_chunks"] += 1
                err_text = chunk.error if hasattr(chunk, "error") else str(chunk)
                self.buffer.hook_stats["errors"].append(err_text)

        except Exception as e:
            logger.error(f"[AgentBridge] Error in on_stream_token: {e}")

    def on_tool_call(self, name: str, arguments: dict[str, Any], tool_call_id: str = "") -> None:
        """
        处理工具调用

        BaseAgentLoop 在调用工具前会调用此钩子
        """
        try:
            # 使用传入的 tool_call_id 或生成新的
            actual_tool_call_id = tool_call_id or f"call_{self._get_next_message_id()}"

            # 创建工具调用对象 (OpenAI 格式)
            tool_call_obj = ChatCompletionMessageToolCall(
                id=actual_tool_call_id,
                type="function",
                function={
                    "name": name,
                    "arguments": json.dumps(arguments) if isinstance(arguments, dict) else str(arguments),
                }
            )
            # 同时保存 dict 格式用于广播
            tool_call_dict = tool_call_obj.to_dict()
            self.buffer.tool_calls.append(tool_call_dict)
            self.buffer.hook_stats["tool_calls"].append({
                "name": name,
                "arguments": arguments if isinstance(arguments, dict) else {"raw": str(arguments)},
            })

            # 确保 _current_assistant_message 存在（模型可能直接调用工具而不输出内容）
            if self._current_assistant_message is None:
                self._current_assistant_message = self._create_assistant_message()
                # 发送开始事件
                self._safe_broadcast("message_start", {
                    "message_id": self._current_assistant_message.id,
                    "role": "assistant",
                    "agent_name": self.agent_name,
                })
                logger.debug(f"[AgentBridge] Created assistant message for tool-only response: {self._current_assistant_message.id}")

            self._safe_broadcast("tool_call", {
                "message_id": self._current_assistant_message.id,
                "tool_call": tool_call_dict,
            })

            # 同时保存到对话框历史 (使用对象类型)
            if not self._current_assistant_message.tool_calls:
                self._current_assistant_message.tool_calls = []
            self._current_assistant_message.tool_calls.append(tool_call_obj)
            logger.debug(f"[AgentBridge] Added tool_call {actual_tool_call_id} to assistant message {self._current_assistant_message.id}")

        except Exception as e:
            logger.error(f"[AgentBridge] Error in on_tool_call: {e}")

    def on_tool_result(self, name: str, result: str, assistant_message: dict[str, Any] | None = None, tool_call_id: str = ""):
        """
        处理工具执行结果

        BaseAgentLoop 在工具执行完成后会调用此钩子
        """
        logger.debug(f"[AgentBridge] on_tool_result called: name={name}, tool_call_id={tool_call_id}")
        try:
            # 生成工具结果消息 ID
            result_message_id = f"{self._get_next_message_id()}_result"

            # 广播工具执行结果
            logger.debug(f"[AgentBridge] Broadcasting tool_result for {tool_call_id}")
            self._safe_broadcast("tool_result", {
                "message_id": self._current_assistant_message.id if self._current_assistant_message else None,
                "tool_call_id": tool_call_id or f"call_{result_message_id}",
                "tool_name": name,
                "result": result,
                "timestamp": time.time(),
            })

            # 创建工具结果消息并保存到对话框历史
            from ..models import ChatMessage
            actual_result = str(result)
            tool_result_msg = ChatMessage.tool(
                content=actual_result,
                tool_call_id=tool_call_id or f"call_{result_message_id}",
                name=name,
            )
            tool_result_msg.id = result_message_id
            event_manager.add_chat_message(self.dialog_id, tool_result_msg)

            logger.debug(f"[AgentBridge] Tool result broadcast: {name} -> {actual_result[:100]}...")

        except Exception as e:
            logger.error(f"[AgentBridge] Error in on_tool_result: {e}")

    def on_complete(self, final_content: str):
        """
        处理完成事件

        BaseAgentLoop 在一轮对话完成时调用此钩子
        """
        try:
            # 保存最终消息到对话框
            if self._current_assistant_message:
                self._current_assistant_message.content = final_content or self.buffer.content
                event_manager.add_chat_message(self.dialog_id, self._current_assistant_message)
                self.buffer.hook_stats["complete_payload"] = self._current_assistant_message.content

                logger.debug(f"[AgentBridge] on_complete: Saved assistant message {self._current_assistant_message.id} "
                           f"with {len(self._current_assistant_message.tool_calls or [])} tool_calls")

                # 发送完成事件
                self._safe_broadcast("message_complete", {
                    "message_id": self._current_assistant_message.id,
                    "content": self._current_assistant_message.content,
                    "reasoning_content": self.buffer.reasoning_content,
                    "tool_calls": self.buffer.tool_calls,
                })
            else:
                logger.warning(f"[AgentBridge] on_complete: _current_assistant_message is None, nothing to save")
            import pathlib
            #以存jsonl格式保存完整对话
            output_dir = pathlib.Path(".logs")
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"{self.dialog_id}_messages.jsonl"

            # 保存消息和 usage 到 JSONL
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(self.buffer.to_dict(), ensure_ascii=False, default=str) + "\n")

        except Exception as e:
            logger.error(f"[AgentBridge] Error in on_complete: {e}")

    def on_reasoning(self, reasoning_content: str):
        """
        处理推理内容（思考过程）

        用于支持 DeepSeek-R1 等推理模型
        """
        try:
            self.buffer.reasoning_content += reasoning_content

            self._safe_broadcast("reasoning", {
                "message_id": self._current_assistant_message.id if self._current_assistant_message else None,
                "reasoning_content": reasoning_content,
            })

        except Exception as e:
            logger.error(f"[AgentBridge] Error in on_reasoning: {e}")

    def on_error(self, error: Exception):
        """
        处理错误

        BaseAgentLoop 在发生错误时调用此钩子
        """
        try:
            error_msg = str(error)
            logger.error(f"[AgentBridge] Agent error: {error_msg}")
            self.buffer.hook_stats["errors"].append(error_msg)

            self._safe_broadcast("error", {
                "message_id": self._current_assistant_message.id if self._current_assistant_message else None,
                "error": error_msg,
            })

            # 发送系统错误消息
            system_msg = ChatMessage.system(f"Agent error: {error_msg}")
            event_manager.add_chat_message(self.dialog_id, system_msg)

        except Exception as e:
            logger.error(f"[AgentBridge] Error in on_error: {e}")

    def on_stop(self):
        """
        处理停止请求

        BaseAgentLoop 在被请求停止时调用此钩子
        """
        try:
            self._safe_broadcast("stopped", {
                "message_id": self._current_assistant_message.id if self._current_assistant_message else None,
            })

        except Exception as e:
            logger.error(f"[AgentBridge] Error in on_stop: {e}")

    def on_after_run(self, messages: list[dict[str, Any]], rounds: int) -> None:
        self.buffer.hook_stats["after_run_rounds"] = rounds

        run_report = {
            "result": str(self.buffer.hook_stats.get("complete_payload", "")),
            "hook_stats": self.buffer.hook_stats,
            "messages": self._serialize_messages(messages),
        }

        self._safe_broadcast("run_summary", run_report)

        # Persist the latest report for offline inspection.
        output_dir = Path(".logs")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{self.dialog_id}_run_report.json"
        output_file.write_text(
            json.dumps(run_report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        cleared, removed = clear_workspace_dir(Path.cwd())
        if cleared:
            logger.debug(f"[AgentBridge] Auto-cleared .workspace, removed={removed}")

        # Reset run-scoped state only after summary is sent.
        self.buffer.reset()
        self._current_assistant_message = None

    def _serialize_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create a stable, JSON-friendly snapshot of OpenAI-style messages."""
        out: list[dict[str, Any]] = []
        for msg in messages:
            item: dict[str, Any] = {
                "role": msg.get("role"),
                "content": msg.get("content"),
            }
            if "tool_call_id" in msg:
                item["tool_call_id"] = msg.get("tool_call_id")
            if "reasoning_content" in msg:
                item["reasoning_content"] = msg.get("reasoning_content")
            if "tool_calls" in msg:
                item["tool_calls"] = msg.get("tool_calls")
            out.append(item)
        return out

    def on_hook(self, hook: HookName, **payload: Any) -> None:
        logger.debug(f"[AgentBridge] on_hook called: {hook}")
        super().on_hook(hook, **payload)

    def get_hook_kwargs(self) -> dict[str, Callable]:
        """
        获取所有钩子函数的字典，用于传递给 BaseAgentLoop

        使用方式:
            bridge = AgentWebSocketBridge(dialog_id="xxx")
            agent = TeamLeadAgent(
                dialog_id=dialog_id,
                **bridge.get_hook_kwargs()
            )
        """
        return {
            "on_stream_token": self.on_stream_token,
            "on_tool_call": self.on_tool_call,
            "on_tool_result": self.on_tool_result,
            "on_complete": self.on_complete,
            "on_reasoning": self.on_reasoning,
            "on_before_run": self.on_before_run,
            "on_after_run": self.on_after_run,
            "on_error": self.on_error,
            "on_stop": self.on_stop,
        }
