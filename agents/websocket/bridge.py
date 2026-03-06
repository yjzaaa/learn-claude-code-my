"""
WebSocket桥接器

将Agent循环与WebSocket事件系统集成
提供回调函数供BaseAgentLoop使用
"""

from loguru import logger
import asyncio
from typing import Any, Optional, Dict
import uuid

from .event_manager import (
    event_manager,
)
from .server import AgentMessageBridge


class WebSocketBridge:
    """
    WebSocket桥接器

    连接Agent循环和WebSocket服务器，将Agent执行过程中的事件
    实时发送到前端
    """

    def __init__(self, dialog_id: Optional[str] = None):
        self.dialog_id = dialog_id or str(uuid.uuid4())
        self.message_bridge: Optional[AgentMessageBridge] = None
        self._current_assistant_message_id: Optional[str] = None
        self._current_tool_call_id: Optional[str] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def initialize(self, title: str = "Agent对话"):
        """初始化对话框"""
        # Do not recreate an existing dialog; recreating wipes in-memory messages.
        if not event_manager.get_dialog(self.dialog_id):
            event_manager.create_dialog(self.dialog_id, title)
        self.message_bridge = AgentMessageBridge(self.dialog_id)
        self._loop = asyncio.get_event_loop()

    # ========== BaseAgentLoop钩子函数 ==========

    def on_before_round(self, messages: list[Dict[str, Any]]):
        """每轮开始前的回调"""
        if not self.message_bridge or not self._loop:
            return

        # 发送系统事件 - 使用 run_coroutine_threadsafe 因为这是在同步回调中
        asyncio.run_coroutine_threadsafe(
            self.message_bridge.send_system_event(
                f"开始新一轮对话，当前消息数: {len(messages)}",
                metadata={"round_start": True, "message_count": len(messages)}
            ),
            self._loop
        )

    def on_stream_token(self, token: str, block: Any, messages: list[Dict[str, Any]], response: Any):
        """流式token回调"""
        try:
            if not self.message_bridge or not self._loop:
                logger.info(f"[WebSocketBridge] on_stream_token skipped: message_bridge={self.message_bridge is not None}, _loop={self._loop is not None}")
                return

            # 如果没有活动的助手消息，创建一个
            if not self._current_assistant_message_id:
                logger.info(f"[WebSocketBridge] Creating new assistant message")
                message = asyncio.run_coroutine_threadsafe(
                    self.message_bridge.start_assistant_response(),
                    self._loop
                ).result(timeout=5)  # 添加超时
                self._current_assistant_message_id = message.id
                # 同步更新 AgentMessageBridge 的 current_message_id
                self.message_bridge.current_message_id = message.id
                logger.info(f"[WebSocketBridge] Created message: {message.id}")
            # 发送流式token - 使用 run_coroutine_threadsafe 因为这是在同步回调中
            future = asyncio.run_coroutine_threadsafe(
                self.message_bridge.send_stream_token(token),
                self._loop
            )
            # 不等待结果，避免阻塞
        except Exception as e:
            logger.info(f"[WebSocketBridge] on_stream_token error: {e}")
            import traceback
            traceback.print_exc()

    def on_stream_text(self, text: str, block: Any, messages: list[Dict[str, Any]], response: Any):
        """流式文本回调"""
        if not self.message_bridge or not self._loop:
            return

        # thinking 单独作为 assistant_thinking 子消息发送。
        if "<thinking>" in text or "思考" in text:
            thinking_content = self._extract_thinking(text)
            if thinking_content:
                asyncio.run_coroutine_threadsafe(
                    self.message_bridge.send_thinking(thinking_content),
                    self._loop
                )
                return

        # 普通文本也要映射为 assistant_text，避免关闭 token 流后前端只看到工具消息。
        if text:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.message_bridge.append_assistant_text(text),
                    self._loop,
                ).result(timeout=5)
                self._current_assistant_message_id = self.message_bridge.current_message_id
            except Exception as e:
                logger.info(f"[WebSocketBridge] on_stream_text append error: {e}")

    def on_tool_call(self, tool_name: str, tool_input: Dict[str, Any], messages: list[Dict[str, Any]]):
        """工具调用开始回调"""
        try:
            logger.info(f"[WebSocketBridge] on_tool_call: {tool_name}")
            if not self.message_bridge or not self._loop:
                return

            message = asyncio.run_coroutine_threadsafe(
                self.message_bridge.send_tool_call(tool_name, tool_input),
                self._loop
            ).result(timeout=5)
            self._current_tool_call_id = message.id
            logger.info(f"[WebSocketBridge] Tool call message created: {message.id}")
        except Exception as e:
            logger.info(f"[WebSocketBridge] on_tool_call error: {e}")
            import traceback
            traceback.print_exc()

    def on_tool_result(self, block: Any, output: str, results: list[Dict[str, Any]], messages: list[Dict[str, Any]]):
        """工具结果回调

        Args:
            block: ToolUseBlock 对象，包含 tool_use_id 和 name 等信息
            output: 工具输出的字符串结果
            results: 所有工具结果列表
            messages: 当前消息列表
        """
        try:
            tool_name = getattr(block, 'name', 'unknown')
            logger.info(f"[WebSocketBridge] on_tool_result: {tool_name}, output length={len(output) if output else 0}")
            if not self.message_bridge or not self._loop:
                return

            # 发送工具结果
            if self._current_tool_call_id:
                asyncio.run_coroutine_threadsafe(
                    self.message_bridge.send_tool_result(
                        self._current_tool_call_id,
                        output or "(no output)"
                    ),
                    self._loop
                ).result(timeout=5)
                self._current_tool_call_id = None
        except Exception as e:
            logger.info(f"[WebSocketBridge] on_tool_result error: {e}")
            import traceback
            traceback.print_exc()

    def on_round_end(self, messages: list[Dict[str, Any]], tool_calls: list[Dict[str, Any]], response: Any):
        """每轮结束回调"""
        try:
            logger.info(f"[WebSocketBridge] on_round_end called, current_message_id={self._current_assistant_message_id}")
            if not self.message_bridge or not self._loop:
                return

            # 获取最终内容
            final_content = self._extract_final_content(response)

            # 如果有活动的助手消息，完成它
            if self._current_assistant_message_id:
                logger.info(f"[WebSocketBridge] Completing message {self._current_assistant_message_id} with content length={len(final_content)}")
                asyncio.run_coroutine_threadsafe(
                    self.message_bridge.complete_assistant_response(final_content),
                    self._loop
                ).result(timeout=5)
                self._current_assistant_message_id = None
                self.message_bridge.current_message_id = None
            elif final_content:
                # 兜底：某些回合可能没有触发流式 token，需补写最终 assistant 文本
                asyncio.run_coroutine_threadsafe(
                    self.message_bridge.send_completed_assistant_text(final_content),
                    self._loop,
                ).result(timeout=5)

            # 轮级兜底：即使当前回合没有显式完成，也不要遗留 streaming 状态到前端。
            asyncio.run_coroutine_threadsafe(
                self.message_bridge.finalize_streaming_messages(),
                self._loop,
            ).result(timeout=5)
        except Exception as e:
            logger.info(f"[WebSocketBridge] on_round_end error: {e}")
            import traceback
            traceback.print_exc()

    def on_after_round(self, messages: list[Dict[str, Any]], response: Any):
        """每轮结束后回调"""
        pass

    def on_stop(self, messages: list[Dict[str, Any]], response: Any):
        """停止回调"""
        try:
            logger.info(f"[WebSocketBridge] on_stop called, current_message_id={self._current_assistant_message_id}")
            if not self.message_bridge or not self._loop:
                return

            final_content = self._extract_final_content(response) if response else ""

            # 如果有活动的助手消息，完成它（on_round_end 在这种情况下不会被调用）
            if self._current_assistant_message_id:
                logger.info(f"[WebSocketBridge] Completing message {self._current_assistant_message_id} in on_stop")
                asyncio.run_coroutine_threadsafe(
                    self.message_bridge.complete_assistant_response(final_content),
                    self._loop
                ).result(timeout=5)
                self._current_assistant_message_id = None
                self.message_bridge.current_message_id = None
            elif final_content:
                # 兜底：无流式消息时也要把最终回答写入对话
                asyncio.run_coroutine_threadsafe(
                    self.message_bridge.send_completed_assistant_text(final_content),
                    self._loop,
                ).result(timeout=5)

            # 最终兜底：避免前端残留 assistant_text=streaming 状态
            asyncio.run_coroutine_threadsafe(
                self.message_bridge.finalize_streaming_messages(),
                self._loop
            ).result(timeout=5)

            asyncio.run_coroutine_threadsafe(
                self.message_bridge.send_system_event(
                    "对话结束",
                    metadata={"stop": True, "final_message_count": len(messages)}
                ),
                self._loop
            )
        except Exception as e:
            logger.info(f"[WebSocketBridge] on_stop error: {e}")
            import traceback
            traceback.print_exc()

    # ========== 工具调用相关 ==========

    async def send_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """发送工具调用消息"""
        if not self.message_bridge:
            return ""

        message = await self.message_bridge.send_tool_call(tool_name, tool_input)
        self._current_tool_call_id = message.id
        return message.id

    async def send_user_message(self, content: str) -> str:
        """发送用户消息"""
        if not self.message_bridge:
            return ""

        message = await self.message_bridge.send_user_message(content)
        return message.id

    # ========== 辅助方法 ==========

    def _extract_thinking(self, text: str) -> str:
        """从文本中提取thinking内容"""
        # 支持 <thinking>标签
        import re
        match = re.search(r'<thinking>(.*?)</thinking>', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 支持特定的思考标记
        if "思考:" in text:
            parts = text.split("思考:", 1)
            if len(parts) > 1:
                return parts[1].strip()

        return ""

    def _format_result(self, result: Any) -> str:
        """格式化结果为字符串"""
        if isinstance(result, str):
            return result
        try:
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        except:
            return str(result)

    def _extract_final_content(self, response: Any) -> str:
        """从响应中提取最终内容"""
        content = getattr(response, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text", "")
                    if text:
                        texts.append(text)
                else:
                    text = getattr(block, "text", "")
                    if text:
                        texts.append(text)
            return "\n".join(texts)
        return ""


class WebSocketToolHandler:
    """
    WebSocket工具处理包装器

    包装工具调用，在调用前后发送WebSocket事件
    """

    def __init__(self, bridge: WebSocketBridge):
        self.bridge = bridge

    async def wrap_tool_call(self, tool_name: str, tool_input: Dict[str, Any], handler: callable) -> Any:
        """包装工具调用"""
        # 发送工具调用开始事件
        await self.bridge.send_tool_call(tool_name, tool_input)

        try:
            # 执行工具
            result = await handler(tool_input) if asyncio.iscoroutinefunction(handler) else handler(tool_input)

            return result
        except Exception as e:
            # 发送错误事件
            if self.bridge.message_bridge:
                await self.bridge.message_bridge.send_system_event(
                    f"工具调用错误: {str(e)}",
                    metadata={"tool_name": tool_name, "error": str(e)}
                )
            raise


def create_websocket_hooks(dialog_id: Optional[str] = None, title: str = "Agent对话") -> tuple[WebSocketBridge, Dict[str, Any]]:
    """
    创建WebSocket钩子函数

    返回:
        (bridge, hooks_dict) - WebSocket桥接器和钩子函数字典
    """
    bridge = WebSocketBridge(dialog_id)

    hooks = {
        "on_before_round": bridge.on_before_round,
        "on_stream_token": bridge.on_stream_token,
        "on_stream_text": bridge.on_stream_text,
        "on_tool_call": bridge.on_tool_call,
        "on_tool_result": bridge.on_tool_result,
        "on_round_end": bridge.on_round_end,
        "on_after_round": bridge.on_after_round,
        "on_stop": bridge.on_stop,
    }

    return bridge, hooks


# 全局桥接器实例（可选）
_global_bridge: Optional[WebSocketBridge] = None


def get_global_bridge() -> Optional[WebSocketBridge]:
    """获取全局WebSocket桥接器"""
    return _global_bridge


def set_global_bridge(bridge: WebSocketBridge):
    """设置全局WebSocket桥接器"""
    global _global_bridge
    _global_bridge = bridge

