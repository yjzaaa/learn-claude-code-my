"""
StateManagedAgentBridge - 状态管理型 Agent Bridge

这是后端状态管理的唯一真实数据源实现。
任何状态变更都会立即广播快照到前端。
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from loguru import logger

try:
    from ..models.dialog_types import (
        DialogSession,
        DialogStatus,
        Message,
        MessageStatus,
        Role,
        ContentType,
        ToolCall,
        ToolCallStatus,
        DialogSummary,
    )
    from ..websocket.server import connection_manager
    from ..base.abstract.hooks import FullAgentHooks, HookName
    from ..session.history_utils import append_history_round, build_window_messages as build_window_messages_from_rounds
    from ..utils.workspace_cleanup import clear_workspace_dir
except ImportError:
    from agents.models.dialog_types import (
        DialogSession,
        DialogStatus,
        Message,
        MessageStatus,
        Role,
        ContentType,
        ToolCall,
        ToolCallStatus,
        DialogSummary,
    )
    from agents.websocket.server import connection_manager
    from agents.base.abstract.hooks import FullAgentHooks, HookName
    from agents.session.history_utils import append_history_round, build_window_messages as build_window_messages_from_rounds
    from agents.utils.workspace_cleanup import clear_workspace_dir


class StateManagedAgentBridge(FullAgentHooks):
    """
    状态管理型 Agent Bridge

    维护 DialogSession 完整状态，任何状态变更立即广播快照。
    """

    def __init__(self, dialog_id: str, agent_name: str = "TeamLeadAgent"):
        self.dialog_id = dialog_id
        self.agent_name = agent_name
        self.session = DialogSession.create_new(
            dialog_id=dialog_id,
            title="Agent 对话",
            agent_name=agent_name,
        )
        window_rounds_raw = os.getenv("SESSION_WINDOW_ROUNDS", "10")
        try:
            # 环境变量配置窗口轮数，默认为 10，最小为 1。
            self.window_rounds = max(1, int(window_rounds_raw))
        except ValueError:
            self.window_rounds = 10
        self.history_rounds: list[dict[str, str]] = []
        self.pending_round: Optional[dict[str, str]] = None
        self._snapshot_history_dir = Path.cwd() / "history"
        self._snapshot_history_dir.mkdir(parents=True, exist_ok=True)
        self._snapshot_history_file = self._snapshot_history_dir / f"{dialog_id}.jsonl"
        self._last_broadcast_task: Optional[asyncio.Task] = None
        logger.debug(f"[StateBridge] Created session for dialog {dialog_id}")

    # ===== 状态查询方法 =====

    def get_session(self) -> DialogSession:
        """获取当前会话状态（只读）"""
        return self.session

    def to_snapshot(self) -> dict:
        """生成状态快照"""
        return {
            "type": "dialog:snapshot",
            "dialog_id": self.dialog_id,
            "data": self.session.to_dict(),
            "timestamp": time.time(),
        }

    def to_summary(self) -> DialogSummary:
        """生成对话框摘要"""
        return DialogSummary(
            id=self.dialog_id,
            title=self.session.title,
            message_count=len(self.session.messages),
            updated_at=self.session.updated_at,
        )

    # ===== 私有广播方法 =====

    async def _broadcast(self, event: dict):
        """广播事件到所有 WebSocket 客户端"""
        try:
            await connection_manager.broadcast(event)
        except Exception as e:
            logger.error(f"[StateBridge] Broadcast error: {e}")

    def _schedule_broadcast(self, event: dict):
        """串行调度广播，确保事件顺序稳定。"""

        async def _chained_broadcast(previous: Optional[asyncio.Task], payload: dict):
            if previous:
                try:
                    await previous
                except Exception:
                    # 前一个广播失败不应阻塞后续事件。
                    pass
            await self._broadcast(payload)

        previous_task = self._last_broadcast_task
        task = asyncio.create_task(_chained_broadcast(previous_task, event))
        self._last_broadcast_task = task

    async def flush_pending_events(self):
        """等待当前桥接器已排队的广播事件发送完成。"""
        task = self._last_broadcast_task
        if task:
            try:
                await task
            except Exception as e:
                logger.error(f"[StateBridge] flush_pending_events error: {e}")

    def _push_snapshot(self, persist: bool = False):
        """推送完整状态快照；仅在显式标记时落盘。"""
        snapshot = self.to_snapshot()
        # 仅在轮次收尾时持久化，并且避免 token 级别写入放大。
        if persist and self.session.streaming_message is None:
            self._persist_snapshot(snapshot)
        self._schedule_broadcast(snapshot)
        logger.debug(f"[StateBridge] Pushed snapshot for {self.dialog_id}, status={self.session.status.value}")

    def _persist_snapshot(self, snapshot: dict) -> None:
        """将非流式快照落盘到 history/<dialog_id>.jsonl。"""
        try:
            with self._snapshot_history_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(snapshot, ensure_ascii=False))
                fh.write("\n")
        except Exception as e:
            logger.error(f"[StateBridge] Persist snapshot error: {e}")

    def _push_delta(self, message_id: str, delta: dict):
        """推送流式增量"""
        event = {
            "type": "stream:delta",
            "dialog_id": self.dialog_id,
            "message_id": message_id,
            "delta": delta,
            "timestamp": time.time(),
        }
        self._schedule_broadcast(event)

    def _push_tool_call_update(self, tool_call: ToolCall):
        """推送工具调用状态更新"""
        event = {
            "type": "tool_call:update",
            "dialog_id": self.dialog_id,
            "tool_call": tool_call.to_dict(),
            "timestamp": time.time(),
        }
        self._schedule_broadcast(event)

    def _push_status_change(self, old_status: DialogStatus, new_status: DialogStatus):
        """推送状态变更"""
        event = {
            "type": "status:change",
            "dialog_id": self.dialog_id,
            "from": old_status.value,
            "to": new_status.value,
            "timestamp": time.time(),
        }
        self._schedule_broadcast(event)

    def emit_custom_event(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """推送自定义事件到当前对话订阅方。"""
        payload = {
            "type": event_type,
            "dialog_id": self.dialog_id,
            "timestamp": time.time(),
        }
        if data:
            payload.update(data)
        self._schedule_broadcast(payload)

    def _gen_id(self, prefix: str = "msg") -> str:
        """生成唯一ID"""
        return f"{prefix}_{self.dialog_id}_{int(time.time() * 1000)}"

    # ===== 用户交互方法 =====

    def on_user_input(self, content: str) -> Message:
        """用户输入处理"""
        user_msg = Message(
            id=self._gen_id("user"),
            role=Role.USER,
            content=content,
            content_type=ContentType.TEXT,
            status=MessageStatus.COMPLETED,
        )

        self.session.add_message(user_msg)
        self.session.status = DialogStatus.THINKING
        self.session.update_timestamp()

        # 推送快照（包含新用户消息和状态变更）
        self._push_snapshot()
        logger.debug(f"[StateBridge] User input added, dialog status: {self.session.status.value}")

        return user_msg

    def _get_last_user_question(self) -> str:
        """获取最近一条用户消息内容。"""
        for message in reversed(self.session.messages):
            if message.role == Role.USER:
                return (message.content or "").strip()
        return ""

    def _capture_pending_round(self) -> None:
        """在暂停时保存未完成的 user/assistant 轮次，供后续恢复。"""
        if not self.session.streaming_message:
            return

        last_user = self._get_last_user_question()
        partial_answer = (self.session.streaming_message.content or "").strip()
        if not last_user or not partial_answer:
            return

        self.pending_round = {
            "user": last_user,
            "assistant": partial_answer,
        }

    def _consume_pending_round(self, current_user: str | None) -> tuple[Optional[dict[str, str]], bool]:
        """读取待恢复轮次，并判断是否为同一用户问题的继续。"""
        if not self.pending_round:
            return None, False

        pending = dict(self.pending_round)
        current_text = (current_user or "").strip()
        is_resume_same_turn = bool(current_text) and current_text == pending["user"]
        return pending, is_resume_same_turn

    # ===== Agent Hook Handlers =====

    def on_before_run(self, messages: list[dict[str, Any]]) -> None:
        """运行前重置状态"""
        # 重置流式消息
        self.session.streaming_message = None
        self.session.status = DialogStatus.THINKING
        logger.debug(f"[StateBridge] Run started, status: {self.session.status.value}")

    def _ensure_streaming_message(self) -> Message:
        """确保流式消息存在"""
        if not self.session.streaming_message:
            assistant_msg = Message(
                id=self._gen_id("assistant"),
                role=Role.ASSISTANT,
                content="",
                content_type=ContentType.MARKDOWN,
                tool_calls=[],
                reasoning_content="",
                agent_name=self.agent_name,
                status=MessageStatus.STREAMING,
            )
            self.session.streaming_message = assistant_msg
            self.session.status = DialogStatus.THINKING
            self.session.update_timestamp()
            self._push_snapshot()
            logger.debug(f"[StateBridge] Stream started, message_id: {assistant_msg.id}")
        return self.session.streaming_message

    def on_stream_token(self, chunk: Any) -> None:
        """处理流式 token (符合 FullAgentHooks 接口)"""
        # 确保流式消息存在
        self._ensure_streaming_message()

        # 根据 chunk 类型处理
        if hasattr(chunk, 'is_content') and chunk.is_content:
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            if self.session.streaming_message:
                self.session.streaming_message.content += content
                self.session.update_timestamp()
                self._push_delta(
                    self.session.streaming_message.id,
                    {"content": content}
                )

        elif hasattr(chunk, 'is_reasoning') and chunk.is_reasoning:
            reasoning = chunk.reasoning_content if hasattr(chunk, 'reasoning_content') else str(chunk)
            if self.session.streaming_message:
                self.session.streaming_message.reasoning_content = (
                    (self.session.streaming_message.reasoning_content or "") + reasoning
                )
                self.session.update_timestamp()
                self._push_delta(
                    self.session.streaming_message.id,
                    {"reasoning": reasoning}
                )

    def on_tool_call(self, name: str, arguments: dict[str, Any], tool_call_id: str = "") -> ToolCall:
        """工具调用"""
        # 确保流式消息存在
        streaming_msg = self._ensure_streaming_message()

        actual_id = tool_call_id or self._gen_id("call")

        tool_call = ToolCall(
            id=actual_id,
            name=name,
            arguments=arguments,
            status=ToolCallStatus.PENDING,
        )

        streaming_msg.tool_calls = streaming_msg.tool_calls or []
        streaming_msg.tool_calls.append(tool_call)
        self.session.metadata.tool_calls_count += 1
        self.session.status = DialogStatus.TOOL_CALLING
        self.session.update_timestamp()

        self._push_snapshot()
        logger.debug(f"[StateBridge] Tool call added: {name}, id: {actual_id}")

        return tool_call

    def on_tool_start(self, tool_call_id: str):
        """工具开始执行"""
        tool = self.session.get_tool_call(tool_call_id)
        if tool:
            tool.status = ToolCallStatus.RUNNING
            tool.started_at = datetime.now().isoformat()
            self.session.update_timestamp()

            self._push_tool_call_update(tool)
            logger.debug(f"[StateBridge] Tool started: {tool_call_id}")

    def on_tool_result(self, name: str, result: str, assistant_message: dict[str, Any] | None = None, tool_call_id: str = ""):
        """工具执行完成"""
        actual_id = tool_call_id or self._gen_id("call")
        tool = self.session.get_tool_call(actual_id)

        if tool:
            tool.status = ToolCallStatus.COMPLETED
            tool.result = result
            tool.completed_at = datetime.now().isoformat()

            # 添加 tool 消息到消息列表
            tool_msg = Message(
                id=self._gen_id("tool"),
                role=Role.TOOL,
                content=result,
                tool_call_id=actual_id,
                tool_name=tool.name,
                status=MessageStatus.COMPLETED,
            )
            self.session.add_message(tool_msg)

            self._push_tool_call_update(tool)
            logger.debug(f"[StateBridge] Tool completed: {tool.name}")
        else:
            logger.warning(f"[StateBridge] Tool not found: {actual_id}")

    def on_complete(self, content: str):
        """流式输出完成 (符合 FullAgentHooks 接口)"""
        if self.session.streaming_message:
            # 如果传入了 content，更新内容
            if content:
                self.session.streaming_message.content = content
            self.session.streaming_message.status = MessageStatus.COMPLETED
            self.session.add_message(self.session.streaming_message)
            self.session.streaming_message = None

        # 检查是否还有未完成的工具调用
        if self._has_pending_tool_calls():
            old_status = self.session.status
            self.session.status = DialogStatus.TOOL_CALLING
            self._push_status_change(old_status, self.session.status)
        else:
            old_status = self.session.status
            self.session.status = DialogStatus.COMPLETED
            self._push_status_change(old_status, self.session.status)

        self._push_snapshot()
        logger.debug(f"[StateBridge] Stream completed, status: {self.session.status.value}")

    def on_after_run(self, messages: list[dict[str, Any]], rounds: int) -> None:
        """运行结束后清理"""
        # 确保流式消息被正确保存
        if self.session.streaming_message:
            self.session.streaming_message.status = MessageStatus.COMPLETED
            self.session.add_message(self.session.streaming_message)
            self.session.streaming_message = None

        # 最终状态更新
        if self.session.status not in (DialogStatus.ERROR, DialogStatus.COMPLETED):
            old_status = self.session.status
            self.session.status = DialogStatus.COMPLETED
            self._push_status_change(old_status, self.session.status)

        self._push_snapshot()
        logger.debug(f"[StateBridge] Run completed, rounds: {rounds}")

        cleared, removed = clear_workspace_dir(Path.cwd())
        if cleared:
            logger.debug(f"[StateBridge] Auto-cleared .workspace, removed={removed}")

    def on_error(self, error: Exception):
        """错误处理"""
        old_status = self.session.status
        self.session.status = DialogStatus.ERROR

        # 添加错误消息
        error_msg = Message(
            id=self._gen_id("error"),
            role=Role.SYSTEM,
            content=str(error),
            status=MessageStatus.ERROR,
        )
        self.session.add_message(error_msg)

        self._push_status_change(old_status, self.session.status)
        self._push_snapshot()
        logger.error(f"[StateBridge] Error: {error}")

    def on_stop(self):
        """停止处理"""
        old_status = self.session.status

        self._capture_pending_round()

        # 保存当前的流式消息
        if self.session.streaming_message:
            self.session.streaming_message.status = MessageStatus.COMPLETED
            self.session.add_message(self.session.streaming_message)
            self.session.streaming_message = None

        self.session.status = DialogStatus.IDLE
        self._push_status_change(old_status, self.session.status)
        self._push_snapshot(persist=True)
        logger.debug(f"[StateBridge] Stopped")

    # ===== 辅助方法 =====

    def append_history_round(self, user_question: str, final_answer: str) -> None:
        """追加一轮历史，仅保留 user + final assistant。"""
        user_text = (user_question or "").strip()
        answer_text = (final_answer or "").strip()

        pending, is_resume_same_turn = self._consume_pending_round(user_text)
        if pending and not is_resume_same_turn:
            append_history_round(
                self.history_rounds,
                pending["user"],
                pending["assistant"],
            )

        if pending and is_resume_same_turn:
            answer_text = f"{pending['assistant']}{answer_text}".strip()

        append_history_round(self.history_rounds, user_text, answer_text)
        self.pending_round = None

    def build_window_messages(self, current_user: str, window_rounds: Optional[int] = None) -> list[dict[str, Any]]:
        """按滑动窗口构建 OpenAI messages（仅 user/assistant + 当前 user）。"""
        limit = self.window_rounds if window_rounds is None else max(1, int(window_rounds))
        pending, is_resume_same_turn = self._consume_pending_round(current_user)

        history_rounds = list(self.history_rounds)
        if pending:
            history_rounds.append(pending)

        effective_user = current_user
        if pending and is_resume_same_turn:
            effective_user = "Continue from your last unfinished answer. Keep the same context, do not restart, and continue seamlessly from the partial answer above."

        return build_window_messages_from_rounds(
            history_rounds,
            current_user=effective_user,
            window_rounds=limit,
        )

    def _has_pending_tool_calls(self) -> bool:
        """检查是否有未完成的工具调用"""
        if self.session.streaming_message and self.session.streaming_message.tool_calls:
            return any(
                t.status in (ToolCallStatus.PENDING, ToolCallStatus.RUNNING)
                for t in self.session.streaming_message.tool_calls
            )
        return False


class DialogStore:
    """
    对话框存储

    管理所有活跃的对话框会话。
    """

    _instance: Optional['DialogStore'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._sessions: dict[str, DialogSession] = {}
        self._bridges: dict[str, StateManagedAgentBridge] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._initialized = True

    def create_dialog(self, dialog_id: str, title: str = "新对话", agent_name: str = "TeamLeadAgent") -> StateManagedAgentBridge:
        """创建新对话框"""
        bridge = StateManagedAgentBridge(dialog_id, agent_name)
        self._sessions[dialog_id] = bridge.get_session()
        self._bridges[dialog_id] = bridge
        logger.debug(f"[DialogStore] Created dialog: {dialog_id}")
        return bridge

    def get_bridge(self, dialog_id: str) -> Optional[StateManagedAgentBridge]:
        """获取 Bridge"""
        return self._bridges.get(dialog_id)

    def get_session(self, dialog_id: str) -> Optional[DialogSession]:
        """获取会话状态"""
        bridge = self._bridges.get(dialog_id)
        if bridge:
            return bridge.get_session()
        return None

    def get_summary(self, dialog_id: str) -> Optional[DialogSummary]:
        """获取摘要"""
        bridge = self._bridges.get(dialog_id)
        if bridge:
            return bridge.to_summary()
        return None

    def list_dialogs(self) -> list[DialogSummary]:
        """列出所有对话框"""
        return [b.to_summary() for b in self._bridges.values()]

    def delete_dialog(self, dialog_id: str) -> bool:
        """删除对话框"""
        if dialog_id in self._bridges:
            del self._bridges[dialog_id]
            if dialog_id in self._sessions:
                del self._sessions[dialog_id]
            self._tasks.pop(dialog_id, None)
            logger.debug(f"[DialogStore] Deleted dialog: {dialog_id}")
            return True
        return False

    def set_task(self, dialog_id: str, task: asyncio.Task) -> None:
        """记录对话框对应的运行任务。"""
        self._tasks[dialog_id] = task

    def get_task(self, dialog_id: str) -> Optional[asyncio.Task]:
        """获取对话框运行任务。"""
        return self._tasks.get(dialog_id)

    def clear_task(self, dialog_id: str, task: Optional[asyncio.Task] = None) -> None:
        """清理任务引用，避免取消已替换的新任务。"""
        current = self._tasks.get(dialog_id)
        if not current:
            return
        if task is not None and current is not task:
            return
        self._tasks.pop(dialog_id, None)

    def cancel_task(self, dialog_id: str) -> bool:
        """取消对话框当前任务。"""
        task = self._tasks.get(dialog_id)
        if task and not task.done():
            task.cancel()
            return True
        return False


# 全局存储实例
dialog_store = DialogStore()
