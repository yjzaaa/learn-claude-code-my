"""请求上下文管理

使用 contextvars 存储当前请求的 user_id，使 MemoryMiddleware 能够动态获取。
同时提供线程/协程安全的存储机制。
"""

import contextvars
from typing import Optional

# 当前请求的用户ID
_current_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "user_id", default=None
)

# 当前请求的项目路径
_current_project_path: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "project_path", default=None
)

# 全局存储（用于在异步任务中丢失 contextvars 时回退）
_user_id_store: dict[str, str] = {}
_project_path_store: dict[str, str] = {}


def set_current_user_id(user_id: str, task_id: str | None = None) -> None:
    """设置当前请求的用户ID"""
    _current_user_id.set(user_id)
    if task_id:
        _user_id_store[task_id] = user_id


def get_current_user_id(task_id: str | None = None) -> Optional[str]:
    """获取当前请求的用户ID"""
    # 首先尝试 contextvars
    user_id = _current_user_id.get()
    if user_id:
        return user_id
    # 回退到全局存储
    if task_id and task_id in _user_id_store:
        return _user_id_store[task_id]
    return None


def set_current_project_path(project_path: str, task_id: str | None = None) -> None:
    """设置当前请求的项目路径"""
    _current_project_path.set(project_path)
    if task_id:
        _project_path_store[task_id] = project_path


def get_current_project_path(task_id: str | None = None) -> Optional[str]:
    """获取当前请求的项目路径"""
    # 首先尝试 contextvars
    path = _current_project_path.get()
    if path is not None:
        return path
    # 回退到全局存储
    if task_id and task_id in _project_path_store:
        return _project_path_store[task_id]
    return ""


def clear_context(task_id: str | None = None) -> None:
    """清除当前请求的上下文"""
    _current_user_id.set(None)
    _current_project_path.set(None)
    if task_id:
        _user_id_store.pop(task_id, None)
        _project_path_store.pop(task_id, None)
