"""
Agent Runtime Bridge - AgentRuntime 管理（简化版）

只负责 Runtime 生命周期管理，不处理广播。
广播统一由 EventHandlers 通过 EventBus 处理。
"""

from __future__ import annotations

from typing import Any

from backend.logging import get_logger

logger = get_logger(__name__)


class AgentRuntimeBridge:
    """
    Agent Runtime 桥接层 - 仅管理 Runtime 生命周期
    广播已移除，统一由 EventHandlers 处理
    """

    def __init__(self, runtime: Any | None = None):
        self._runtime = runtime

    @property
    def runtime(self) -> Any | None:
        """获取当前 Runtime 实例"""
        return self._runtime

    def set_runtime(self, runtime: Any) -> None:
        """设置 Runtime 实例"""
        self._runtime = runtime
        logger.info(
            "[AgentRuntimeBridge] Runtime injected: %s", getattr(runtime, "runtime_id", "unknown")
        )

    async def initialize_runtime(self, config: dict[str, Any] | None = None) -> Any:
        """初始化 Runtime"""
        from backend.domain.models.shared.config import EngineConfig
        from backend.infrastructure.runtime.runtime_factory import AgentRuntimeFactory

        if self._runtime is None:
            engine_config = EngineConfig.model_validate(config or {})
            factory = AgentRuntimeFactory()
            self._runtime = factory.create(
                agent_type="simple",
                agent_id="default",
                config=engine_config,
            )
            logger.info("[AgentRuntimeBridge] Runtime created")
        return self._runtime

    async def shutdown_runtime(self) -> None:
        """关闭 Runtime"""
        if self._runtime:
            await self._runtime.shutdown()
            self._runtime = None
            logger.info("[AgentRuntimeBridge] Runtime shutdown")

    async def create_dialog(self, user_input: str, title: str | None = None) -> str:
        """创建新对话"""
        if not self._runtime:
            await self.initialize_runtime()

        if self._runtime is None:
            raise RuntimeError("[AgentRuntimeBridge] Runtime initialization failed")

        dialog_id = await self._runtime.create_dialog(user_input, title)
        return dialog_id

    def get_dialog(self, dialog_id: str) -> Any | None:
        """获取对话"""
        if not self._runtime:
            return None
        return self._runtime.get_dialog(dialog_id)

    def list_dialogs(self) -> list[Any]:
        """列出所有对话"""
        if not self._runtime:
            return []
        return self._runtime.list_dialogs()

    async def stop_dialog(self, dialog_id: str) -> bool:
        """停止指定对话的 Agent"""
        if not self._runtime:
            return False

        try:
            await self._runtime.stop(dialog_id)
            logger.info(f"[AgentRuntimeBridge] Stopped dialog: {dialog_id}")
            return True
        except Exception as e:
            logger.error(f"[AgentRuntimeBridge] Error stopping dialog {dialog_id}: {e}")
            return False


__all__ = ["AgentRuntimeBridge"]
