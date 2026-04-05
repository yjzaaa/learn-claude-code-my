"""Deep Model Switcher Mixin - 模型切换功能

从 deep_legacy.py 提取的模型动态切换逻辑。
"""

import os
from pathlib import Path
from typing import Any, Optional
from loguru import logger

from backend.infrastructure.services import ProviderManager


class DeepModelSwitcherMixin:
    """模型切换 Mixin"""

    _agent: Any
    _config: Any
    _model_name: Optional[str]
    _agent_id: str
    _checkpointer: Any
    _store: Any
    _tools: dict
    _provider_manager: Optional[ProviderManager]

    async def _ensure_agent_for_dialog(self, dialog_id: str) -> bool:
        """
        确保 agent 使用正确的模型（支持动态模型切换）

        Args:
            dialog_id: 对话 ID

        Returns:
            如果重新创建了 agent 返回 True，否则返回 False
        """
        logger.info(f"[_ensure_agent_for_dialog] Checking model for dialog={dialog_id}, current_model={self._model_name}")

        if not self._provider_manager:
            logger.warning("[_ensure_agent_for_dialog] No provider_manager available")
            return False

        # 获取对话选择的模型
        try:
            from backend.infrastructure.container import container
            if not container.session_manager:
                logger.warning("[_ensure_agent_for_dialog] No session_manager in container")
                return False

            session = container.session_manager.get_session_sync(dialog_id)
            if not session:
                logger.warning(f"[_ensure_agent_for_dialog] Session not found for dialog={dialog_id}")
                return False

            selected_model = getattr(session, 'selected_model_id', None)
            logger.info(f"[_ensure_agent_for_dialog] Session found, selected_model={selected_model}, current={self._model_name}")

            if not selected_model:
                logger.info(f"[_ensure_agent_for_dialog] No selected_model for dialog={dialog_id}")
                return False

            if selected_model == self._model_name:
                logger.info(f"[_ensure_agent_for_dialog] Model unchanged: {self._model_name}")
                return False

            # 模型需要切换
            logger.info(
                f"[DeepAgentRuntime] Model changed from {self._model_name} to {selected_model} for dialog {dialog_id}"
            )
            # 重新创建模型实例
            new_model = await self._provider_manager.create_model_instance(selected_model)
            self._model_name = selected_model

            # 重新创建 agent builder
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
            skills_dir = project_root / "skills"

            # 创建 backend（与 _do_initialize 保持一致）
            agent_sandbox = os.getenv("AGENT_SANDBOX", "local").strip().lower()
            if agent_sandbox == "docker":
                from backend.infrastructure.runtime.deep.services.docker_sandbox_backend import create_sandbox_backend
                backend = create_sandbox_backend(root_dir=str(skills_dir), virtual_mode=True, inherit_env=True)
            else:
                from backend.infrastructure.runtime.deep.services.windows_shell_backend import WindowsShellBackend
                backend = WindowsShellBackend(root_dir=str(skills_dir), virtual_mode=True, inherit_env=True)

            # 转换工具格式
            from langchain_core.tools import StructuredTool
            adapted_tools = [
                StructuredTool.from_function(
                    func=tool_info.handler,
                    name=name,
                    description=tool_info.description,
                )
                for name, tool_info in self._tools.items()
            ]

            # 重新构建 agent
            from ..agents import AgentBuilder
            base_prompt = self._config.system or self._config.system_prompt or ""
            system_prompt = base_prompt + (
                "\n\n## Environment\n"
                "You run inside a Linux Docker container. "
                "Use Linux commands (ls, cat, grep, cd). "
            )

            builder = (
                AgentBuilder()
                .with_name(self._config.name or self._agent_id)
                .with_model(new_model)
                .with_tools(adapted_tools)
                .with_system_prompt(system_prompt)
                .with_backend(backend)
                .with_checkpointer(self._checkpointer)
                .with_store(self._store)
                .with_skills(self._config.skills or [])
                .with_todo_list()
                .with_filesystem()
                .with_claude_compression(level="standard", enable_session_memory=True)
                .with_prompt_caching()
            )

            if self._config.interrupt_on:
                builder.with_human_in_the_loop(interrupt_on=self._config.interrupt_on)

            self._agent = builder.build()
            logger.info(f"[DeepAgentRuntime] Rebuilt agent with new model: {selected_model}")
            return True
        except Exception as e:
            logger.error(f"[DeepAgentRuntime] Failed to check/switch model: {e}")
            import traceback
            logger.error(traceback.format_exc())

        return False
