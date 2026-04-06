"""
Memory Types - 记忆类型定义

避免循环导入的基础类型定义。
"""

from enum import Enum


class MemoryType(str, Enum):
    """记忆类型枚举"""

    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"
