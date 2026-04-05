"""Model Switch Manager - 模型切换管理

处理动态模型切换逻辑。
"""

from typing import Any, Optional

from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ModelSwitchManager:
    """模型切换管理器

    职责:
    - 检查是否需要切换模型
    - 获取对话选择的模型
    - 重建 Agent
    """

    def __init__(self, runtime: "DeepAgentRuntime"):
        self.runtime = runtime

    async def check_and_switch(self, dialog_id: str) -> bool:
        """检查并执行模型切换

        Args:
            dialog_id: 对话 ID

        Returns:
            如果切换了模型返回 True
        """
        if not self.runtime._provider_manager:
            return False

        selected_model = await self._get_selected_model(dialog_id)
        if not selected_model:
            return False

        if selected_model == self.runtime._model_name:
            return False

        await self._rebuild_agent(selected_model)
        return True

    async def _get_selected_model(self, dialog_id: str) -> Optional[str]:
        """获取对话选择的模型"""
        try:
            from backend.infrastructure.container import container
            if not container.session_manager:
                return None

            session = container.session_manager.get_session_sync(dialog_id)
            if not session:
                return None

            return getattr(session, 'selected_model_id', None)
        except Exception as e:
            logger.debug(f"[ModelSwitch] Could not get selected model: {e}")
            return None

    async def _rebuild_agent(self, new_model: str) -> None:
        """重建 Agent"""
        logger.info(f"[ModelSwitch] Rebuilding agent with model: {new_model}")

        # 创建新模型实例
        new_model_instance = await self.runtime._provider_manager.create_model_instance(new_model)
        self.runtime._model_name = new_model

        # 重建 agent（使用现有配置）
        await self._do_rebuild(new_model_instance)

    async def _do_rebuild(self, model_instance: Any) -> None:
        """执行重建"""
        from langchain_core.tools import StructuredTool

        # 转换工具
        adapted_tools = [
            StructuredTool.from_function(
                func=tool_info.handler,
                name=name,
                description=tool_info.description,
            )
            for name, tool_info in self.runtime._agent_mgr.tools.items()
        ]

        # 使用 AgentBuilder 重建
        from backend.infrastructure.runtime.deep.agents import AgentBuilder

        base_prompt = self.runtime._config.system or self.runtime._config.system_prompt or ""
        system_prompt = base_prompt + (
            "\n\n## Environment\n"
            "You run inside a Linux Docker container. "
            "Use Linux commands (ls, cat, grep, cd). "
        )

        builder = (
            AgentBuilder()
            .with_name(self.runtime._config.name or self.runtime._agent_id)
            .with_model(model_instance)
            .with_tools(adapted_tools)
            .with_system_prompt(system_prompt)
            .with_backend(self.runtime._backend)
            .with_checkpointer(self.runtime._checkpointer)
            .with_store(self.runtime._store)
            .with_skills(self.runtime._config.skills or [])
            .with_todo_list()
            .with_filesystem()
            .with_claude_compression(level="standard", enable_session_memory=True)
            .with_prompt_caching()
        )

        if self.runtime._config.interrupt_on:
            builder.with_human_in_the_loop(interrupt_on=self.runtime._config.interrupt_on)

        self.runtime._agent = builder.build()
        logger.info(f"[ModelSwitch] Agent rebuilt with new model")


__all__ = ["ModelSwitchManager"]
