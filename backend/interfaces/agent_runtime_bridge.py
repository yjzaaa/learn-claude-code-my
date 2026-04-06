"""
Agent Runtime Bridge - AgentRuntime 桥接层

实现 IAgentRuntimeBridge 接口，协调 AgentRuntime 执行与 WebSocket 广播。
连接新的 Runtime 架构和传输层。
使用自定义消息类（继承自 LangChain BaseMessage）。
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Dict

from loguru import logger
from langchain_core.messages import BaseMessage, message_to_dict
from pydantic import BaseModel

from backend.infrastructure.protocols.interfaces import IAgentRuntimeBridge
from backend.infrastructure.runtime.interfaces import IAgentRuntime
from backend.domain.models import (
    CustomHumanMessage,
    CustomAIMessage,
    make_status_change,
)
from backend.domain.models.shared.types import OpenAIToolCall, OpenAIFunction
from backend.domain.models.events.websocket import WSDialogSnapshot, WSDialogMetadata, WSSnapshotEvent, WSErrorEvent, WSErrorDetail, WSHitlRequestEvent
from backend.interfaces.websocket import ws_broadcaster


class AgentRuntimeBridge(IAgentRuntimeBridge):
    """
    Agent Runtime 桥接层 - 协调 Runtime 执行与事件广播

    职责:
    - 管理 AgentRuntime 实例（通过 AgentFactory 创建）
    - 管理对话状态 (status, streaming_message)
    - 执行 Agent 运行循环
    - 广播事件到 WebSocket 客户端
    - 支持流检查点恢复
    - 使用自定义消息类进行消息处理

    与 AgentBridge 的区别:
    - 使用 AgentRuntime 而非 AgentEngine
    - 处理 AgentEvent 事件流而非原始文本流
    - 使用自定义消息类 (CustomHumanMessage, CustomAIMessage 等)
    - 支持更丰富的流式事件（工具调用、HITL 等）
    """

    def __init__(self, runtime: Optional[IAgentRuntime] = None):
        """
        初始化桥接层

        Args:
            runtime: 可选的预配置 Runtime 实例。可以通过 set_runtime 后续注入
        """
        self._runtime = runtime
        self._bcast = ws_broadcaster

        # dialog_id → "idle" | "thinking" | "completed" | "error"
        self._status: dict[str, str] = dict()  # noqa: bare-dict
        # dialog_id → current streaming CustomAIMessage (or None)
        self._streaming_msg: dict[str, Optional[CustomAIMessage]] = dict()  # noqa: bare-dict
        # dialog_id → message_id → chunk_index (用于检查点)
        self._chunk_counters: dict[str, dict[str, int]] = dict()  # noqa: bare-dict
        # dialog_id → message_id → accumulated_content (用于恢复)
        self._stream_buffers: dict[str, dict[str, str]] = dict()  # noqa: bare-dict
        # dialog_id → list of tool calls in current stream
        self._streaming_tools: dict[str, list] = dict()  # noqa: bare-dict

    def _iso(self) -> str:
        """ISO 格式时间戳"""
        return datetime.now(timezone.utc).isoformat()

    def _ts(self) -> int:
        """毫秒时间戳"""
        return self._bcast._ts()

    async def _broadcast(self, event: Any, dialog_id: Optional[str] = None) -> None:
        """广播事件到 WebSocket 客户端"""
        await self._bcast.broadcast(event, dialog_id)

    @property
    def connection_manager(self):
        """获取连接管理器"""
        return self._bcast.connection_manager

    @property
    def runtime(self) -> Optional[IAgentRuntime]:
        """获取当前 Runtime 实例"""
        return self._runtime

    def set_runtime(self, runtime: IAgentRuntime) -> None:
        """
        设置 Runtime 实例（依赖注入）

        Args:
            runtime: IAgentRuntime 实例
        """
        self._runtime = runtime
        logger.info("[AgentRuntimeBridge] Runtime injected: %s", runtime.runtime_id)

    async def initialize_runtime(self, config: Optional[dict[str, Any]] = None) -> IAgentRuntime:  # noqa: bare-dict
        """
        初始化 Runtime（如果未提供）- 向后兼容

        Args:
            config: Runtime 配置字典

        Returns:
            初始化后的 Runtime 实例

        Note:
            推荐使用 set_runtime() 注入预配置的 Runtime
        """
        from backend.domain.models.shared.config import EngineConfig
        from backend.infrastructure.runtime.runtime_factory import AgentRuntimeFactory

        if self._runtime is None:
            engine_config = EngineConfig.model_validate(config or {})
            factory = AgentRuntimeFactory()
            self._runtime = factory.create(
                agent_type="simple",
                agent_id="default",
                config=engine_config,
            )
            # 注意：这里只创建但不初始化，初始化由调用方负责
            logger.info("[AgentRuntimeBridge] Runtime created via AgentRuntimeFactory (not initialized)")
        return self._runtime

    async def shutdown_runtime(self) -> None:
        """关闭 Runtime"""
        if self._runtime:
            await self._runtime.shutdown()
            self._runtime = None
            logger.info("[AgentRuntimeBridge] Runtime shutdown")

    def _make_message_dict(self, msg: BaseMessage) -> dict[str, Any]:
        """转换 BaseMessage 为字典（LangChain 格式）"""
        return message_to_dict(msg)

    def _dialog_to_snapshot(self, dialog_id: str) -> Optional[WSDialogSnapshot]:
        """转换 Dialog 为快照模型"""
        if not self._runtime:
            return None

        dialog = self._runtime.get_dialog(dialog_id)
        if not dialog:
            return None

        # 处理 BaseModel、Dialog 类或 dict 类型的 dialog
        if isinstance(dialog, BaseModel):
            dialog_data = dialog.model_dump()
            dialog_id_val = getattr(dialog, 'id', dialog_data.get('id'))
            dialog_title = getattr(dialog, 'title', dialog_data.get('title', 'New Dialog'))
            messages = getattr(dialog, 'messages', dialog_data.get('messages', []))
            created_at = getattr(dialog, 'created_at', dialog_data.get('created_at'))
            updated_at = getattr(dialog, 'updated_at', dialog_data.get('updated_at'))
        elif hasattr(dialog, 'id') and hasattr(dialog, 'messages'):
            # Dialog 类或其他类似对象
            dialog_id_val = getattr(dialog, 'id', None)
            dialog_title = getattr(dialog, 'title', 'New Dialog')
            messages = getattr(dialog, 'messages', [])
            created_at = getattr(dialog, 'created_at', None)
            updated_at = getattr(dialog, 'updated_at', None)
        else:
            dialog_id_val = dialog.get('id')
            dialog_title = dialog.get('title', 'New Dialog')
            messages = dialog.get('messages', [])
            created_at = dialog.get('created_at')
            updated_at = dialog.get('updated_at')

        # 使用 message_to_dict 序列化所有消息
        msgs = [self._make_message_dict(m) for m in messages]

        # 构建流式消息
        streaming_msg = self._streaming_msg.get(dialog_id)
        from backend.domain.models.events.websocket import WSStreamingMessage
        ws_streaming = None
        if streaming_msg is not None:
            ws_streaming = WSStreamingMessage(
                id=streaming_msg.msg_id or "",
                message=streaming_msg.model_dump(),
                status=streaming_msg.status,
                timestamp=self._iso(),
                agent_name=streaming_msg.agent_name,
            )

        return WSDialogSnapshot(
            id=dialog_id_val,
            title=dialog_title or "New Dialog",
            status=self._status.get(dialog_id, "idle"),
            messages=msgs,
            streaming_message=ws_streaming,
            metadata=WSDialogMetadata(
                model="",
                agent_name="Agent",
                tool_calls_count=0,
                total_tokens=0,
            ),
            created_at=created_at.isoformat() if isinstance(created_at, datetime) else str(created_at) if created_at else self._iso(),
            updated_at=updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at) if updated_at else self._iso(),
        )

    async def run_agent(
        self,
        dialog_id: str,
        content: str,
        client_message_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> None:
        """
        运行 Agent 并广播事件

        Args:
            dialog_id: 对话 ID（如果为空则创建新对话）
            content: 用户输入内容
            client_message_id: 前端预生成的消息ID（可选）
            title: 对话标题（仅在新对话时使用）
        """
        logger.info(f"[AgentRuntimeBridge] run_agent started: dialog_id={dialog_id}")
        if not self._runtime:
            await self.initialize_runtime()

        # 确保 runtime 已初始化
        if self._runtime is None:
            raise RuntimeError("[AgentRuntimeBridge] Runtime initialization failed")

        # 使用前端传入的ID或生成新ID
        msg_id = client_message_id or f"msg_{uuid.uuid4().hex[:12]}"

        # 初始化检查点计数器
        if dialog_id not in self._chunk_counters:
            self._chunk_counters[dialog_id] = dict()
        if dialog_id not in self._stream_buffers:
            self._stream_buffers[dialog_id] = dict()
        if dialog_id not in self._streaming_tools:
            self._streaming_tools[dialog_id] = []

        self._chunk_counters[dialog_id][msg_id] = 0
        self._stream_buffers[dialog_id][msg_id] = ""
        self._streaming_tools[dialog_id] = []

        # 设置流式消息占位 - 使用 CustomAIMessage
        self._status[dialog_id] = "thinking"
        self._streaming_msg[dialog_id] = CustomAIMessage(
            content="",
            msg_id=msg_id,
            agent_name="Agent",
            status="streaming",
        )

        await self._broadcast(
            make_status_change(dialog_id, "idle", "thinking", self._ts()),
            dialog_id
        )

        accumulated = ""
        accumulated_reasoning = ""
        chunk_index = 0
        has_error = False

        try:
            # 如果是新对话，先创建
            if not self._runtime.get_dialog(dialog_id):
                dialog_id = await self._runtime.create_dialog(content, title)

            # 发送流开始事件 - 使用 CustomAIMessage
            stream_start_msg = CustomAIMessage(
                content="",
                msg_id=msg_id,
                agent_name="Agent",
                status="streaming",
            )
            await self._bcast.broadcast_stream_start(
                dialog_id, msg_id, message=stream_start_msg
            )

            # 调用 Runtime 的 send_message 并处理 AgentEvent 流
            # type: ignore[attr-defined]
            logger.info(f"[AgentRuntimeBridge] Starting to receive events from runtime")
            event_count = 0
            async for event in self._runtime.send_message(dialog_id, content, stream=True):  # type: ignore[attr-defined]
                event_count += 1
                logger.info(f"[AgentRuntimeBridge] Received event #{event_count}: type={event.type}")
                # 第一个事件到达时发送初始快照
                if accumulated == "":
                    snap = self._dialog_to_snapshot(dialog_id)
                    if snap:
                        snap_event = WSSnapshotEvent(
                            dialog_id=dialog_id,
                            data=snap,
                            timestamp=self._ts(),
                        )
                        await self._broadcast(snap_event, dialog_id)

                # 处理不同类型的事件
                if event.type == "model_complete":
                    data = event.data if isinstance(event.data, dict) else {}
                    messages = data.get("messages", [])
                    node = data.get("node", "model")

                    # 提取最后一条 AIMessage 的 content
                    ai_content = ""
                    for m in messages:
                        if m.get("type") == "ai":
                            ai_content = m.get("data", {}).get("content", "")
                            break

                    accumulated += ai_content
                    chunk_index += 1

                    # 更新流式消息
                    sm = self._streaming_msg.get(dialog_id)
                    if sm is not None:
                        sm.content = accumulated
                        sm.status = "completed"

                    # 更新检查点
                    self._chunk_counters[dialog_id][msg_id] = chunk_index
                    self._stream_buffers[dialog_id][msg_id] = accumulated

                    # 广播节点更新事件
                    logger.info(f"[AgentRuntimeBridge] Broadcasting node_update: dialog_id={dialog_id}, node={node}, messages={len(messages)}")
                    await self._bcast.broadcast_node_update(
                        dialog_id=dialog_id,
                        node=node,
                        messages=messages,
                    )
                    logger.info(f"[AgentRuntimeBridge] Node update broadcasted successfully")

                elif event.type == "node_update":
                    data = event.data if isinstance(event.data, dict) else {}
                    messages = data.get("messages", [])
                    node = data.get("node", "unknown")

                    logger.info(f"[AgentRuntimeBridge] Node update: {node}, messages={len(messages)}")
                    await self._bcast.broadcast_node_update(
                        dialog_id=dialog_id,
                        node=node,
                        messages=messages,
                    )

                elif event.type == "text_delta":
                    # 兼容旧 messages 模式 / SimpleRuntime
                    chunk = str(event.data)
                    accumulated += chunk
                    chunk_index += 1

                    sm = self._streaming_msg.get(dialog_id)
                    if sm is not None:
                        sm.content = accumulated

                    self._chunk_counters[dialog_id][msg_id] = chunk_index
                    self._stream_buffers[dialog_id][msg_id] = accumulated

                    await self._bcast.broadcast_delta(
                        dialog_id, msg_id, content=chunk, reasoning=""
                    )

                elif event.type == "reasoning_delta":
                    # 处理推理内容增量
                    reasoning_chunk = str(event.data)
                    accumulated_reasoning += reasoning_chunk

                    # 广播 reasoning delta
                    await self._bcast.broadcast_delta(
                        dialog_id, msg_id, content="", reasoning=reasoning_chunk
                    )

                elif event.type == "tool_start":
                    # 工具调用开始（保留兼容处理）
                    tool_data = event.data if isinstance(event.data, dict) else {}
                    tool_name = tool_data.get("name", "unknown")
                    tool_args = tool_data.get("args", {})

                    tool_call = OpenAIToolCall(
                        id=f"call_{uuid.uuid4().hex[:8]}",
                        type="function",
                        function=OpenAIFunction(
                            name=tool_name,
                            arguments=json.dumps(tool_args) if isinstance(tool_args, dict) else str(tool_args),
                        ),
                    )
                    self._streaming_tools[dialog_id].append(tool_call.model_dump())

                    # 更新流式消息的工具调用
                    sm = self._streaming_msg.get(dialog_id)
                    if sm is not None:
                        sm.tool_calls = self._streaming_tools[dialog_id].copy()

                    logger.info(f"[AgentRuntimeBridge] Tool start: {tool_name}")

                elif event.type == "tool_end":
                    # 工具调用结束
                    result = event.data
                    if isinstance(result, dict):
                        logger.info(f"[AgentRuntimeBridge] Tool end: {result.get('tool_name', 'unknown')}")
                    else:
                        logger.info(f"[AgentRuntimeBridge] Tool end: {result}")

                elif event.type in ("complete", "text_complete"):
                    # 对话完成 (处理两种事件名，兼容不同 runtime)
                    logger.info(f"[AgentRuntimeBridge] Dialog complete: {dialog_id}, event_type={event.type}")
                    # 如果有数据，更新累积内容
                    if event.data and isinstance(event.data, str):
                        accumulated = event.data

                elif event.type == "hitl_request":
                    # HITL 中断请求
                    logger.info(f"[AgentRuntimeBridge] HITL request: {dialog_id}")
                    # 广播 HITL 事件到前端
                    hitl_event = WSHitlRequestEvent(
                        dialog_id=dialog_id,
                        data=event.data if isinstance(event.data, dict) else {},
                        timestamp=self._ts(),
                    )
                    await self._broadcast(hitl_event, dialog_id)

                elif event.type == "error":
                    # 错误事件
                    error_msg = str(event.data)
                    logger.error(f"[AgentRuntimeBridge] Error in stream: {error_msg}")
                    has_error = True
                    raise Exception(error_msg)

            # 流完成，创建最终的 CustomAIMessage
            final_msg = CustomAIMessage(
                content=accumulated,
                msg_id=msg_id,
                agent_name="Agent",
                status="completed",
                tool_calls=self._streaming_tools[dialog_id],
            )

            # 发送流结束事件 - 使用最终的 CustomAIMessage
            await self._bcast.broadcast_stream_end(
                dialog_id, msg_id, message=final_msg
            )

            # 发送状态变更
            self._status[dialog_id] = "completed"
            await self._broadcast(
                make_status_change(dialog_id, "thinking", "completed", self._ts()),
                dialog_id
            )

            # 清理流式消息
            self._streaming_msg[dialog_id] = None
            self._status[dialog_id] = "idle"
            self._streaming_tools[dialog_id] = []

            # 清理检查点数据
            self._cleanup_checkpoint(dialog_id, msg_id)

            # 发送最终快照
            final_snap = self._dialog_to_snapshot(dialog_id)
            if final_snap:
                event = WSSnapshotEvent(
                    dialog_id=dialog_id,
                    data=final_snap,
                    timestamp=self._ts(),
                )
                await self._broadcast(event, dialog_id)

        except Exception as exc:
            logger.exception("[AgentRuntimeBridge] Error running dialog %s: %s", dialog_id, exc)
            self._streaming_msg[dialog_id] = None
            self._status[dialog_id] = "error"

            # 发送流截断事件
            await self._bcast.broadcast_stream_truncated(
                dialog_id, msg_id, "error"
            )

            error_event = WSErrorEvent(
                dialog_id=dialog_id,
                error=WSErrorDetail(code="agent_error", message=str(exc)),
                timestamp=self._ts(),
            )
            await self._broadcast(error_event, dialog_id)
            await self._broadcast(
                make_status_change(dialog_id, "thinking", "error", self._ts()),
                dialog_id
            )

    def _cleanup_checkpoint(self, dialog_id: str, message_id: str) -> None:
        """清理检查点数据"""
        if dialog_id in self._chunk_counters and message_id in self._chunk_counters[dialog_id]:
            del self._chunk_counters[dialog_id][message_id]
        if dialog_id in self._stream_buffers and message_id in self._stream_buffers[dialog_id]:
            del self._stream_buffers[dialog_id][message_id]

    def get_last_checkpoint(self, dialog_id: str, message_id: str) -> Optional[tuple[int, str]]:
        """获取最后检查点 (chunk_index, content)"""
        if dialog_id not in self._chunk_counters:
            return None
        if message_id not in self._chunk_counters[dialog_id]:
            return None

        chunk_index = self._chunk_counters[dialog_id][message_id]
        content = self._stream_buffers.get(dialog_id, {}).get(message_id, "")
        return (chunk_index, content)

    def get_status(self, dialog_id: str) -> str:
        """获取对话状态"""
        return self._status.get(dialog_id, "idle")

    def set_status(self, dialog_id: str, status: str) -> None:
        """设置对话状态"""
        self._status[dialog_id] = status

    def init_dialog_state(self, dialog_id: str) -> None:
        """初始化对话状态"""
        self._status[dialog_id] = "idle"
        self._streaming_msg[dialog_id] = None
        self._streaming_tools[dialog_id] = []

    def remove_dialog_state(self, dialog_id: str) -> None:
        """移除对话状态"""
        self._status.pop(dialog_id, None)
        self._streaming_msg.pop(dialog_id, None)
        self._streaming_tools.pop(dialog_id, None)
        self._chunk_counters.pop(dialog_id, None)
        self._stream_buffers.pop(dialog_id, None)

    async def stop_dialog(self, dialog_id: str) -> bool:
        """
        停止指定对话的 Agent

        Returns:
            是否成功停止
        """
        if not self._runtime:
            return False

        try:
            await self._runtime.stop(dialog_id)
            self._status[dialog_id] = "idle"
            self._streaming_msg[dialog_id] = None
            self._streaming_tools[dialog_id] = []
            logger.info(f"[AgentRuntimeBridge] Stopped dialog: {dialog_id}")
            return True
        except Exception as e:
            logger.error(f"[AgentRuntimeBridge] Error stopping dialog {dialog_id}: {e}")
            return False

    def stop_all(self) -> list[str]:
        """
        停止所有运行的 Agent，返回被停止的对话 ID 列表
        """
        stopped = [k for k, v in self._status.items() if v == "thinking"]
        for k in stopped:
            self._status[k] = "idle"
            self._streaming_msg[k] = None
            self._streaming_tools[k] = []
        return stopped

    def get_snapshot(self, dialog_id: str) -> Optional[WSDialogSnapshot]:
        """获取对话快照"""
        return self._dialog_to_snapshot(dialog_id)

    async def broadcast_snapshot(self, dialog_id: str) -> None:
        """广播当前对话快照到所有订阅的客户端"""
        snap = self._dialog_to_snapshot(dialog_id)
        if snap:
            event = WSSnapshotEvent(
                dialog_id=dialog_id,
                data=snap,
                timestamp=self._ts(),
            )
            await self._broadcast(event, dialog_id)

    async def create_dialog(self, user_input: str, title: Optional[str] = None) -> str:
        """
        创建新对话

        Args:
            user_input: 用户初始输入
            title: 对话标题（可选）

        Returns:
            对话 ID
        """
        if not self._runtime:
            await self.initialize_runtime()

        if self._runtime is None:
            raise RuntimeError("[AgentRuntimeBridge] Runtime initialization failed")

        dialog_id = await self._runtime.create_dialog(user_input, title)
        self.init_dialog_state(dialog_id)
        return dialog_id

    def get_dialog(self, dialog_id: str) -> Optional[Any]:
        """获取对话"""
        if not self._runtime:
            return None
        return self._runtime.get_dialog(dialog_id)

    def list_dialogs(self) -> list[Any]:
        """列出所有对话"""
        if not self._runtime:
            return []
        return self._runtime.list_dialogs()

    def register_tool(
        self,
        name: str,
        handler: Any,
        description: str,
        schema: Optional[BaseModel] = None,
    ) -> None:
        """
        注册工具到 Runtime

        Args:
            name: 工具名称
            handler: 处理函数
            description: 工具描述
            schema: 参数 Schema（Pydantic BaseModel，可选）
        """
        if not self._runtime:
            raise RuntimeError("Runtime not initialized. Call initialize_runtime() first.")

        self._runtime.register_tool(name, handler, description, schema)
        logger.debug(f"[AgentRuntimeBridge] Registered tool: {name}")


__all__ = ["AgentRuntimeBridge"]
