"""
生命周期管理相关功能的 Mixin
"""

import logging

from core.models.events import SystemStarted, SystemStopped
from .base import EngineMixinBase

logger = logging.getLogger(__name__)


class LifecycleMixin(EngineMixinBase):
    """引擎生命周期管理功能"""

    async def startup(self):
        """启动引擎"""
        await self._state_mgr.load()
        self._skill_mgr.load_builtin_skills()
        self._event_bus.emit(SystemStarted())
        logger.info("[AgentEngine] Startup complete")

    async def shutdown(self):
        """关闭引擎"""
        await self._state_mgr.save()
        self._event_bus.emit(SystemStopped())
        self._event_bus.shutdown()
        logger.info("[AgentEngine] Shutdown complete")

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._event_bus.is_running
