"""
Dialog Session Exceptions

重构后的异常层次，继承统一的领域异常基类。
保持向后兼容的导入路径和构造函数。
"""

from backend.domain.exceptions.base import (
    AlreadyExistsError,
    LimitExceededError,
    NotFoundError,
    StateError,
)


class SessionError(Exception):
    """会话基础异常（向后兼容）"""

    pass


class SessionNotFoundError(NotFoundError, SessionError):
    """会话不存在

    继承 NotFoundError 获得标准错误码和序列化能力。
    保留 SessionError 继承以保持向后兼容。
    """

    def __init__(self, dialog_id: str | None = None, message: str | None = None):
        # 优先使用传入的消息，否则使用默认
        msg = message or (
            f"Dialog session not found: {dialog_id}" if dialog_id else "Session not found"
        )
        super().__init__(
            resource_type="DialogSession",
            resource_id=dialog_id,
            message=msg,
        )
        self.dialog_id = dialog_id


class SessionAlreadyExistsError(AlreadyExistsError, SessionError):
    """会话已存在

    继承 AlreadyExistsError 获得标准错误码和序列化能力。
    保留 SessionError 继承以保持向后兼容。
    """

    def __init__(self, dialog_id: str | None = None, message: str | None = None):
        msg = message or (
            f"Dialog session already exists: {dialog_id}" if dialog_id else "Session already exists"
        )
        super().__init__(
            resource_type="DialogSession",
            resource_id=dialog_id,
            message=msg,
        )
        self.dialog_id = dialog_id


class StreamingStateError(StateError, SessionError):
    """流式状态错误

    继承 StateError 获得标准错误码。
    保留 SessionError 继承以保持向后兼容。
    """

    def __init__(self, message: str = "Streaming state error", current_state: str | None = None):
        super().__init__(
            message=message,
            current_state=current_state,
        )


class InvalidTransitionError(StateError, SessionError):
    """无效的状态转换

    继承 StateError 获得标准状态错误处理。
    保留 SessionError 继承和原有构造函数以保持向后兼容。
    """

    def __init__(self, dialog_id: str, from_status: str, to_status: str):
        self.dialog_id = dialog_id
        self.from_status = from_status
        self.to_status = to_status

        message = f"Invalid transition from '{from_status}' to '{to_status}' for dialog {dialog_id}"
        super().__init__(
            message=message,
            current_state=from_status,
            expected_state=f"not {to_status}",
            dialog_id=dialog_id,
        )


class SessionFullError(LimitExceededError, SessionError):
    """会话数量达到上限

    继承 LimitExceededError 获得标准限制错误处理。
    保留 SessionError 继承和原有构造函数以保持向后兼容。
    """

    def __init__(self, max_sessions: int, current: int | None = None):
        self.max_sessions = max_sessions

        message = f"Maximum number of sessions ({max_sessions}) reached"
        super().__init__(
            message=message,
            limit_type="DialogSession",
            current=current,
            maximum=max_sessions,
        )
