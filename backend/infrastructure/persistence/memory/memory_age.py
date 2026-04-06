"""
Memory Age Utilities - 记忆年龄工具

计算记忆的新鲜度和年龄文本表示。
"""

from datetime import datetime

from backend.domain.models.memory import Memory


class MemoryAge:
    """记忆年龄计算工具类"""

    @staticmethod
    def memory_age_days(timestamp: datetime) -> int:
        """计算从 timestamp 到现在的天数

        Args:
            timestamp: 记忆的时间戳

        Returns:
            天数（非负整数）
        """
        delta = datetime.now() - timestamp
        return max(0, delta.days)

    @staticmethod
    def memory_age_text(days: int) -> str:
        """返回年龄文本描述

        Args:
            days: 天数

        Returns:
            "today"/"yesterday"/"{n} days ago"
        """
        if days == 0:
            return "today"
        if days == 1:
            return "yesterday"
        return f"{days} days ago"

    @staticmethod
    def memory_freshness_text(memory: Memory) -> str:
        """如果记忆 >1天，返回警告文本

        Args:
            memory: 记忆实体

        Returns:
            警告文本，如果记忆新鲜则返回空字符串
        """
        age_days = memory.age_days
        if age_days <= 1:
            return ""

        age_text = MemoryAge.memory_age_text(age_days)
        return (
            f"⚠️ This memory is {age_text} old. "
            "Claims may be outdated."
        )

    @staticmethod
    def memory_freshness_note(memory: Memory) -> str:
        """返回包装在 <system-reminder> 中的警告

        Args:
            memory: 记忆实体

        Returns:
            包装后的警告文本，如果记忆新鲜则返回空字符串
        """
        warning = MemoryAge.memory_freshness_text(memory)
        if not warning:
            return ""

        return f"<system-reminder>\n{warning}\n</system-reminder>"

    @staticmethod
    def get_age_text_for_timestamp(timestamp: datetime) -> str:
        """根据时间戳获取年龄文本

        Args:
            timestamp: 时间戳

        Returns:
            年龄文本描述
        """
        days = MemoryAge.memory_age_days(timestamp)
        return MemoryAge.memory_age_text(days)


def memory_age_days(timestamp: datetime) -> int:
    """计算从 timestamp 到现在的天数

    Args:
        timestamp: 记忆的时间戳

    Returns:
        天数（非负整数）
    """
    return MemoryAge.memory_age_days(timestamp)


def memory_age_text(days: int) -> str:
    """返回年龄文本描述

    Args:
        days: 天数

    Returns:
        "today"/"yesterday"/"{n} days ago"
    """
    return MemoryAge.memory_age_text(days)


def memory_freshness_text(memory: Memory) -> str:
    """如果记忆 >1天，返回警告文本

    Args:
        memory: 记忆实体

    Returns:
        警告文本，如果记忆新鲜则返回空字符串
    """
    return MemoryAge.memory_freshness_text(memory)


def memory_freshness_note(memory: Memory) -> str:
    """返回包装在 <system-reminder> 中的警告

    Args:
        memory: 记忆实体

    Returns:
        包装后的警告文本，如果记忆新鲜则返回空字符串
    """
    return MemoryAge.memory_freshness_note(memory)
