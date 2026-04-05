"""Deep Runtime Mixins - 功能模块化拆分

按职责划分的 Mixin 类，保持 deep_legacy.py 功能完整的同时实现代码组织。

使用方式:
    class DeepAgentRuntime(
        DeepInitializerMixin,
        DeepMessageHandlerMixin,
        DeepSkillLoaderMixin,
        DeepSandboxMixin,
        DeepModelSwitcherMixin,
        DeepCheckpointMixin,
        DeepToolManagerMixin,
        DeepStopHandlerMixin,
        AbstractAgentRuntime[DeepAgentConfig],
        DeepLoggingMixin,
    ):
        pass
"""

from .initializer import DeepInitializerMixin
from .message_handler import DeepMessageHandlerMixin
from .skill_loader import DeepSkillLoaderMixin
from .sandbox import DeepSandboxMixin
from .model_switcher import DeepModelSwitcherMixin
from .checkpoint import DeepCheckpointMixin
from .tool_manager import DeepToolManagerMixin
from .stop_handler import DeepStopHandlerMixin

__all__ = [
    "DeepInitializerMixin",
    "DeepMessageHandlerMixin",
    "DeepSkillLoaderMixin",
    "DeepSandboxMixin",
    "DeepModelSwitcherMixin",
    "DeepCheckpointMixin",
    "DeepToolManagerMixin",
    "DeepStopHandlerMixin",
]
