"""Application DTOs - 数据传输对象"""

from .requests import ChatRequest
from .responses import (
    ChatResponse,
    CreateDialogResult,
    LoadSkillResult,
    MemorySummary,
    MessageDTO,
    SendMessageResult,
    SkillInfoDTO,
)

__all__ = [
    "ChatRequest",
    "CreateDialogResult",
    "SendMessageResult",
    "LoadSkillResult",
    "SkillInfoDTO",
    "MessageDTO",
    "MemorySummary",
    "ChatResponse",
]
