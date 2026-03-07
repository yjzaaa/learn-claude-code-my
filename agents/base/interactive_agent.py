"""
交互式 Agent 基类 - 统一前端交互层

将事件管理、消息生命周期、WebSocket 通信统一集成到 BaseAgent 层，
子类只需关注业务逻辑，无需关心前端交互细节。

设计原则:
1. 前后端数据模型完全对齐 (使用 models.py 中的类型)
2. 消息生命周期自动管理 (创建 → 更新 → 完成/错误)
3. 子类通过高阶方法操作消息，无需直接操作事件系统
4. 内置停止信号处理
"""

from __future__ import annotations

import uuid
import asyncio
from typing import Any, Optional, Dict, List, Callable, Union
from loguru import logger

from .base_agent_loop import BaseAgentLoop
from .models import (
    MessageType,
    MessageStatus,
    AgentType,
    RealtimeMessage,
    DialogSession,
    MessageAddedEvent,
    MessageUpdatedEvent,
    StreamTokenEvent,
    AgentState,
)


class FrontendBridge:
    """
    前端桥接器 - 管理消息到前端的传输

    职责:
    1. 维护消息状态 (当前对话 ID、正在流式传输的消息 ID 等)
    2. 发送事件到前端 (通过 EventManager)
    3. 管理消息生命周期
    """

    def __init__(self, dialog_id: str, agent_type: str = "default"):
        self.dialog_id = dialog_id
        self.agent_type = agent_type
        self._current_assistant_msg_id: Optional[str] = None
        self._current_tool_call_id: Optional[str] = None
        self._event_manager = None  # 懒加载
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_event_manager(self):
        """懒加载 EventManager"""
        if self._event_manager is None:
            from ..websocket.event_manager import event_manager
            self._event_manager = event_manager
        return self._event_manager

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """设置事件循环"""
        self._loop = loop

    # ========== 消息生命周期管理 ==========

    def create_user_message(self, content: str) -> RealtimeMessage:
        """创建用户消息"""
        msg = RealtimeMessage.create(
            msg_type=MessageType.USER_MESSAGE,
            content=content,
            status=MessageStatus.COMPLETED,
            agent_type=self.agent_type,
        )
        self._emit_message_added(msg)
        return msg

    def start_assistant_response(self) -> RealtimeMessage:
        """开始助手响应 (流式)"""
        msg = RealtimeMessage.create(
            msg_type=MessageType.ASSISTANT_TEXT,
            content="",
            status=MessageStatus.STREAMING,
            agent_type=self.agent_type,
        )
        self._current_assistant_msg_id = msg.id
        self._emit_message_added(msg)
        return msg

    def send_stream_token(self, token: str) -> None:
        """发送流式 token"""
        if not self._current_assistant_msg_id:
            return

        # 获取或创建消息引用
        event_manager = self._get_event_manager()
        dialog = event_manager.get_dialog(self.dialog_id)
        if not dialog:
            return

        for msg in dialog.messages:
            if msg.id == self._current_assistant_msg_id:
                # 更新消息
                msg.append_token(token)
                msg.agent_type = self.agent_type

                # 发送流式事件
                self._emit_stream_token(msg.id, token, msg.content)
                return

    def send_thinking(self, content: str, parent_id: Optional[str] = None) -> RealtimeMessage:
        """发送思考过程"""
        msg = RealtimeMessage.create(
            msg_type=MessageType.ASSISTANT_THINKING,
            content=content,
            status=MessageStatus.COMPLETED,
            agent_type=self.agent_type,
            parent_id=parent_id or self._current_assistant_msg_id,
        )
        self._emit_message_added(msg)
        return msg

    def send_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        parent_id: Optional[str] = None,
    ) -> RealtimeMessage:
        """发送工具调用"""
        msg = RealtimeMessage.create(
            msg_type=MessageType.TOOL_CALL,
            content=f"调用工具: {tool_name}",
            status=MessageStatus.PENDING,
            agent_type=self.agent_type,
            parent_id=parent_id or self._current_assistant_msg_id,
            tool_name=tool_name,
            tool_input=tool_input,
        )
        self._current_tool_call_id = msg.id
        self._emit_message_added(msg)
        return msg

    def send_tool_result(
        self,
        tool_call_id: str,
        result: str,
    ) -> RealtimeMessage:
        """发送工具结果"""
        msg = RealtimeMessage.create(
            msg_type=MessageType.TOOL_RESULT,
            content=result,
            status=MessageStatus.COMPLETED,
            agent_type=self.agent_type,
            parent_id=tool_call_id,
        )
        self._emit_message_added(msg)

        # 更新工具调用状态为完成
        self._update_message_status(tool_call_id, MessageStatus.COMPLETED)
        return msg

    def complete_assistant_response(self, final_content: Optional[str] = None) -> None:
        """完成助手响应"""
        if self._current_assistant_msg_id:
            updates = {"status": MessageStatus.COMPLETED, "agent_type": self.agent_type}
            if final_content is not None:
                updates["content"] = final_content
            self._update_message(self._current_assistant_msg_id, **updates)
            self._current_assistant_msg_id = None

    def send_system_event(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RealtimeMessage:
        """发送系统事件"""
        msg = RealtimeMessage.create(
            msg_type=MessageType.SYSTEM_EVENT,
            content=content,
            status=MessageStatus.COMPLETED,
            agent_type=self.agent_type,
            metadata=metadata,
        )
        self._emit_message_added(msg)
        return msg

    def finalize_streaming_messages(self) -> None:
        """兜底收口：将遗留的 streaming 消息标记为 completed"""
        event_manager = self._get_event_manager()
        dialog = event_manager.get_dialog(self.dialog_id)
        if not dialog:
            return

        for msg in dialog.messages:
            if msg.status == MessageStatus.STREAMING:
                self._update_message(
                    msg.id,
                    status=MessageStatus.COMPLETED,
                    content=msg.content or "".join(msg.stream_tokens),
                )

    # ========== 内部事件发射方法 ==========

    def _emit_message_added(self, message: RealtimeMessage) -> None:
        """发射消息添加事件"""
        try:
            event_manager = self._get_event_manager()
            # 添加到对话
            from ..websocket.event_manager import RealTimeMessage as EMMessage
            em_msg = EMMessage(
                id=message.id,
                type=event_manager.MessageType(message.type.value),
                content=message.content,
                status=event_manager.MessageStatus(message.status.value),
                tool_name=message.tool_name,
                tool_input=message.tool_input,
                timestamp=message.timestamp,
                metadata=message.metadata,
                parent_id=message.parent_id,
                stream_tokens=message.stream_tokens,
                agent_type=message.agent_type,
            )
            event_manager.add_message_to_dialog(self.dialog_id, em_msg)
        except Exception as e:
            logger.warning(f"[FrontendBridge] Error emitting message_added: {e}")

    def _emit_message_updated(self, message: RealtimeMessage) -> None:
        """发射消息更新事件"""
        try:
            event_manager = self._get_event_manager()
            updates = {
                "content": message.content,
                "status": event_manager.MessageStatus(message.status.value),
                "agent_type": message.agent_type,
                "stream_tokens": message.stream_tokens,
            }
            event_manager.update_message_in_dialog(self.dialog_id, message.id, updates)
        except Exception as e:
            logger.warning(f"[FrontendBridge] Error emitting message_updated: {e}")

    def _emit_stream_token(self, message_id: str, token: str, current_content: str) -> None:
        """发射流式 token 事件"""
        try:
            event_manager = self._get_event_manager()
            event_data = {
                "type": "stream_token",
                "dialog_id": self.dialog_id,
                "message_id": message_id,
                "token": token,
                "current_content": current_content,
            }
            if event_manager.should_push_event(event_data):
                # 广播到订阅者
                asyncio.create_task(
                    event_manager.broadcast_to_clients(event_data)
                )
        except Exception as e:
            logger.debug(f"[FrontendBridge] Error emitting stream_token: {e}")

    def _update_message(self, message_id: str, **updates: Any) -> None:
        """更新消息字段"""
        try:
            event_manager = self._get_event_manager()
            # 转换 status 枚举
            if "status" in updates and isinstance(updates["status"], MessageStatus):
                updates["status"] = event_manager.MessageStatus(updates["status"].value)
            event_manager.update_message_in_dialog(self.dialog_id, message_id, updates)
        except Exception as e:
            logger.warning(f"[FrontendBridge] Error updating message: {e}")

    def _update_message_status(self, message_id: str, status: MessageStatus) -> None:
        """更新消息状态"""
        self._update_message(message_id, status=status)


class BaseInteractiveAgent(BaseAgentLoop):
    """
    交互式 Agent 基类 - 集成前端交互能力

    相比 BaseAgentLoop，增加了:
    1. 内置 FrontendBridge，自动管理消息生命周期
    2. 内置 AgentState，统一管理运行状态
    3. 高阶方法封装，子类只需关注业务逻辑

    使用示例:
        class MyAgent(BaseInteractiveAgent):
            def run(self, messages: list[dict], dialog_id: str) -> None:
                self.initialize_session(dialog_id)

                # 自动创建用户消息
                self.add_user_message("查询数据")

                # 自动流式输出
                with self.assistant_stream():
                    self.stream_text("正在查询...")
                    # ... 执行查询 ...
                    self.stream_text("查询完成")

                # 自动工具调用消息
                with self.tool_execution("sql_query", {"sql": "SELECT ..."}) as tool:
                    result = execute_sql(tool.input)
                    tool.complete(result)

                self.finalize_session()
    """

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        system: str,
        tools: list[Any],
        dialog_id: str,
        agent_type: str = "default",
        max_tokens: int = 8000,
        max_rounds: int | None = 25,
        enable_streaming: bool = True,
    ):
        # 初始化交互组件
        self.dialog_id = dialog_id
        self.agent_type = agent_type
        self.state = AgentState()
        self.bridge = FrontendBridge(dialog_id, agent_type)
        self.enable_streaming = enable_streaming
        self._current_assistant_msg_id: Optional[str] = None
        self._current_tool_call_id: Optional[str] = None

        # 准备回调函数 (桥接到父类的回调系统)
        callbacks = self._build_callbacks()

        # 初始化基类
        super().__init__(
            client=client,
            model=model,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
            max_rounds=max_rounds,
            should_stop=lambda: self.state.check_should_stop(),
            **callbacks,
        )

    def _build_callbacks(self) -> Dict[str, Any]:
        """构建回调函数字典，桥接 FrontendBridge"""
        callbacks = {}

        if self.enable_streaming:
            callbacks["on_stream_token"] = self._on_stream_token
            callbacks["on_stream_text"] = self._on_stream_text

        callbacks["on_tool_call"] = self._on_tool_call
        callbacks["on_tool_result"] = self._on_tool_result
        callbacks["on_before_round"] = self._on_before_round
        callbacks["on_stop"] = self._on_stop

        return callbacks

    # ========== 回调实现 ==========

    def _on_stream_token(self, token: str, block: Any, messages: list, response: Any) -> None:
        """流式 token 回调"""
        if self._current_assistant_msg_id:
            self.bridge.send_stream_token(token)

    def _on_stream_text(self, text: str, block: Any, messages: list, response: Any) -> None:
        """流式文本回调"""
        pass  # 使用 token 级别的流式

    def _on_tool_call(self, tool_name: str, tool_input: dict, messages: list) -> None:
        """工具调用回调"""
        msg = self.bridge.send_tool_call(tool_name, tool_input)
        self._current_tool_call_id = msg.id

    def _on_tool_result(self, block: Any, output: str, results: list, messages: list) -> None:
        """工具结果回调"""
        if self._current_tool_call_id:
            self.bridge.send_tool_result(self._current_tool_call_id, str(output))
            self._current_tool_call_id = None

    def _on_before_round(self, messages: list) -> None:
        """每轮开始回调 - 开始新的助手响应"""
        if not self._current_assistant_msg_id:
            msg = self.bridge.start_assistant_response()
            self._current_assistant_msg_id = msg.id

    def _on_stop(self, messages: list, response: Any) -> None:
        """停止回调"""
        self.bridge.complete_assistant_response()
        self._current_assistant_msg_id = None

    # ========== 高阶 API (子类使用) ==========

    def initialize_session(self) -> None:
        """初始化会话"""
        self.state.start(self.dialog_id, self.agent_type)
        self.bridge.send_system_event(
            f"Agent {self.agent_type} 开始运行",
            {"step": "start", "max_rounds": self.max_rounds},
        )

    def finalize_session(self) -> None:
        """结束会话"""
        self.bridge.finalize_streaming_messages()
        self.bridge.send_system_event(
            "Agent 运行完成",
            {"step": "complete"},
        )
        self.state.reset()

    def add_user_message(self, content: str) -> RealtimeMessage:
        """添加用户消息"""
        return self.bridge.create_user_message(content)

    def stream_text(self, text: str) -> None:
        """流式输出文本 (逐字符)"""
        if not self._current_assistant_msg_id:
            msg = self.bridge.start_assistant_response()
            self._current_assistant_msg_id = msg.id

        for char in text:
            self.bridge.send_stream_token(char)

    def complete_response(self, final_content: Optional[str] = None) -> None:
        """完成当前响应"""
        self.bridge.complete_assistant_response(final_content)
        self._current_assistant_msg_id = None

    def send_thinking(self, content: str) -> RealtimeMessage:
        """发送思考过程"""
        return self.bridge.send_thinking(content)

    def send_error(self, error_message: str) -> RealtimeMessage:
        """发送错误消息"""
        return self.bridge.send_system_event(
            f"错误: {error_message}",
            {"step": "error", "error": error_message},
        )

    def request_stop(self) -> None:
        """请求停止运行"""
        self.state.stop()
        self.bridge.send_system_event("收到停止请求", {"step": "stop_requested"})

    # ========== 上下文管理器 (推荐用法) ==========

    class AssistantStream:
        """助手流式输出上下文管理器"""
        def __init__(self, agent: "BaseInteractiveAgent"):
            self.agent = agent

        def __enter__(self):
            msg = self.agent.bridge.start_assistant_response()
            self.agent._current_assistant_msg_id = msg.id
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.agent.bridge.complete_assistant_response()
            self.agent._current_assistant_msg_id = None
            return False

        def write(self, text: str) -> None:
            """写入文本"""
            self.agent.stream_text(text)

    def assistant_stream(self) -> "AssistantStream":
        """获取流式输出上下文管理器"""
        return self.AssistantStream(self)

    class ToolExecution:
        """工具执行上下文管理器"""
        def __init__(
            self,
            agent: "BaseInteractiveAgent",
            tool_name: str,
            tool_input: Dict[str, Any],
        ):
            self.agent = agent
            self.tool_name = tool_name
            self.tool_input = tool_input
            self.msg_id: Optional[str] = None
            self.result: Optional[str] = None

        def __enter__(self):
            msg = self.agent.bridge.send_tool_call(self.tool_name, self.tool_input)
            self.msg_id = msg.id
            self.agent._current_tool_call_id = msg.id
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.result is not None:
                self.agent.bridge.send_tool_result(self.msg_id, self.result)
            self.agent._current_tool_call_id = None
            return False

        def complete(self, result: str) -> None:
            """完成工具执行"""
            self.result = result

    def tool_execution(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> "ToolExecution":
        """获取工具执行上下文管理器"""
        return self.ToolExecution(self, tool_name, tool_input)


__all__ = [
    "FrontendBridge",
    "BaseInteractiveAgent",
]
