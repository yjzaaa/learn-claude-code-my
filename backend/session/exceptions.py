"""
Dialog Session Exceptions
"""


class SessionError(Exception):
    """会话基础异常"""
    pass


class SessionNotFoundError(SessionError):
    """会话不存在"""
    pass


class SessionAlreadyExistsError(SessionError):
    """会话已存在"""
    pass


class StreamingStateError(SessionError):
    """流式状态错误"""
    pass


class InvalidTransitionError(SessionError):
    """无效的状态转换"""
    def __init__(self, dialog_id: str, from_status: str, to_status: str):
        self.dialog_id = dialog_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Invalid transition from '{from_status}' to '{to_status}' for dialog {dialog_id}")


class SessionFullError(SessionError):
    """会话数量达到上限"""
    def __init__(self, max_sessions: int):
        self.max_sessions = max_sessions
        super().__init__(f"Maximum number of sessions ({max_sessions}) reached")
