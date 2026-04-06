"""Deep Runtime Mixins - 功能模块化拆分

按职责划分的 Mixin 类，保持 deep_legacy.py 功能完整的同时实现代码组织。

使用方式:
    class DeepAgentRuntime(
        AbstractAgentRuntime[DeepAgentConfig],  # Base class FIRST for correct MRO
        DeepLoggingMixin,
        DeepInitializerMixin,
        DeepMessageHandlerMixin,
        DeepSkillLoaderMixin,
        DeepSandboxMixin,
        DeepModelSwitcherMixin,
        DeepCheckpointMixin,
        DeepStopHandlerMixin,
    ):
        pass
"""

from .checkpoint import DeepCheckpointMixin
from .initializer import DeepInitializerMixin
from .message_handler import DeepMessageHandlerMixin
from .model_switcher import DeepModelSwitcherMixin
from .sandbox import DeepSandboxMixin
from .skill_loader import DeepSkillLoaderMixin
from .stop_handler import DeepStopHandlerMixin

__all__ = [
    "DeepInitializerMixin",
    "DeepMessageHandlerMixin",
    "DeepSkillLoaderMixin",
    "DeepSandboxMixin",
    "DeepModelSwitcherMixin",
    "DeepCheckpointMixin",
    "DeepStopHandlerMixin",
]
