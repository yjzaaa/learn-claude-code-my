"""
AgentWebSocketBridge - Agent 与 WebSocket 之间的桥接层

侵入性最小的设计：
1. 通过 BaseAgentLoop 的钩子函数捕获事件
2. 转换为 ChatEvent 并通过 WebSocket 广播
3. 不修改 Agent 内部逻辑，只在外层包装
"""

import asyncio
import json
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from loguru import logger

try:
    from ..models import ChatMessage, ChatEvent, ChatCompletionMessageToolCall
    from ..websocket.server import connection_manager
    from ..websocket.event_manager import event_manager
except ImportError:
    from agents.models import ChatMessage, ChatEvent, ChatCompletionMessageToolCall
    from agents.websocket.server import connection_manager
    from agents.websocket.event_manager import event_manager


@dataclass
class StreamingBuffer:
    """流式内容缓冲区，用于聚合分片内容"""
    content: str = ""
    reasoning_content: str = ""
    tool_calls: list = field(default_factory=list)

    def reset(self):
        self.content = ""
        self.reasoning_content = ""
        self.tool_calls = []


class AgentWebSocketBridge:
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
        logger.info(f"[AgentBridge] Broadcasting event: {event_type}, data keys: {list(data.keys())}")
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
                logger.info(f"[AgentBridge] Content chunk received: {content[:50]}...")

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

                # 发送推理内容
                self._safe_broadcast("reasoning_delta", {
                    "message_id": self._current_assistant_message.id,
                    "delta": reasoning,
                    "reasoning_content": self.buffer.reasoning_content,
                })

        except Exception as e:
            logger.error(f"[AgentBridge] Error in on_stream_token: {e}")

    def on_tool_call(self, tool_name: str, arguments: dict):
        """
        处理工具调用

        BaseAgentLoop 在调用工具前会调用此钩子
        """
        try:
            # 创建工具调用对象 (OpenAI 格式)
            tool_call_obj = ChatCompletionMessageToolCall(
                id=f"call_{self._get_next_message_id()}",
                type="function",
                function={
                    "name": tool_name,
                    "arguments": json.dumps(arguments) if isinstance(arguments, dict) else str(arguments),
                }
            )
            # 同时保存 dict 格式用于广播
            tool_call_dict = tool_call_obj.to_dict()
            self.buffer.tool_calls.append(tool_call_dict)

            self._safe_broadcast("tool_call", {
                "message_id": self._current_assistant_message.id if self._current_assistant_message else None,
                "tool_call": tool_call_dict,
            })

            # 同时保存到对话框历史 (使用对象类型)
            if self._current_assistant_message:
                if not self._current_assistant_message.tool_calls:
                    self._current_assistant_message.tool_calls = []
                self._current_assistant_message.tool_calls.append(tool_call_obj)

        except Exception as e:
            logger.error(f"[AgentBridge] Error in on_tool_call: {e}")

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

                # 发送完成事件
                self._safe_broadcast("message_complete", {
                    "message_id": self._current_assistant_message.id,
                    "content": self._current_assistant_message.content,
                    "reasoning_content": self.buffer.reasoning_content,
                    "tool_calls": self.buffer.tool_calls,
                })
            import pathlib
            #以存jsonl格式保存完整对话
            output_dir = pathlib.Path(".logs")
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"{self.dialog_id}_messages.jsonl"

            # 保存消息和 usage 到 JSONL
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(self.buffer, ensure_ascii=False, default=str) + "\n")

            # 重置缓冲区
            self.buffer.reset()
            self._current_assistant_message = None

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
            "on_complete": self.on_complete,
            "on_reasoning": self.on_reasoning,
            "on_error": self.on_error,
            "on_stop": self.on_stop,
        }
