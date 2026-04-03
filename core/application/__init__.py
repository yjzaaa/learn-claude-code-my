"""
Application Service Layer - 应用服务层

职责:
- 编排业务用例
- 协调多个 Domain 对象
- 不直接操作底层存储，通过 Repository

与 Manager 层区别:
- Manager: 底层管理，直接操作内存/存储
- Service: 高层编排，面向用例

Usage:
    from core.application import DialogService, SkillService
    from core.application.dto import ChatRequest, CreateDialogResult
"""

# Services
from core.application.services import (
    DialogService,
    SkillService,
    MemoryService,
    AgentOrchestrationService,
    DialogNotFoundError,
    SkillNotFoundError,
)

# DTOs
from core.application.dto import (
    ChatRequest,
    CreateDialogResult,
    SendMessageResult,
    LoadSkillResult,
    SkillInfoDTO,
    MessageDTO,
    MemorySummary,
    ChatResponse,
)

__all__ = [
    # Services
    "DialogService",
    "SkillService",
    "MemoryService",
    "AgentOrchestrationService",
    # Exceptions
    "DialogNotFoundError",
    "SkillNotFoundError",
    # DTOs
    "ChatRequest",
    "CreateDialogResult",
    "SendMessageResult",
    "LoadSkillResult",
    "SkillInfoDTO",
    "MessageDTO",
    "MemorySummary",
    "ChatResponse",
]
