"""
Dialog Session Manager - 对话会话管理模块

基于 LangChain ChatMessageHistory 的消息存储，
上层封装会话生命周期和状态管理。

使用示例:
    from core.session import DialogSessionManager, SessionStatus

    mgr = DialogSessionManager()

    # 创建对话
    session = await mgr.create_session("dlg_001", "New Dialog")

    # 添加用户消息
    await mgr.add_user_message("dlg_001", "Hello")

    # 开始 AI 流式响应
    await mgr.start_ai_response("dlg_001", "msg_001")

    # 转发 delta (不存储)
    await mgr.emit_delta("dlg_001", "Hello ")

    # 完成响应 (由外部提供完整内容)
    await mgr.complete_ai_response("dlg_001", "msg_001", "Hello there!")
"""

from .manager import DialogSessionManager
from .models import (
    DialogSession,
    SessionStatus,
    SessionMetadata,
    StreamingContext,
    SessionEvent,
)
from .exceptions import (
    SessionError,
    SessionNotFoundError,
    SessionAlreadyExistsError,
    StreamingStateError,
    InvalidTransitionError,
    SessionFullError,
)

__all__ = [
    # 主类
    "DialogSessionManager",
    # 模型
    "DialogSession",
    "SessionStatus",
    "SessionMetadata",
    "StreamingContext",
    "SessionEvent",
    # 异常
    "SessionError",
    "SessionNotFoundError",
    "SessionAlreadyExistsError",
    "StreamingStateError",
    "InvalidTransitionError",
    "SessionFullError",
]
