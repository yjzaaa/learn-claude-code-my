"""Deep Agent Runtime Facade - 统一入口

基于 deep-agents 框架的 Runtime 实现，使用模块化架构。
这是主要入口，协调各个子模块。
"""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from loguru import logger

from backend.domain.models.shared import AgentEvent
from backend.domain.models.shared.config import EngineConfig
from backend.infrastructure.llm_adapter import (
    LLMResponseAdapterFactory,
)
from backend.infrastructure.runtime.base.runtime import AbstractAgentRuntime, ToolCache
from backend.infrastructure.services import ProviderManager

from .agent import AgentLifecycleManager
from .agents import AgentBuilder
from .checkpoint import CheckpointManager
from .events import EventStreamHandler
from .model import ModelSwitchManager
from .types import DeepAgentConfig


class DeepAgentRuntime(AbstractAgentRuntime[DeepAgentConfig]):
    """Deep Agent Runtime 实现 (Facade)

    基于模块化架构，协调各个子模块：
    - AgentLifecycleManager: 技能加载和工具管理
    - EventStreamHandler: 流式事件处理
    - ModelSwitchManager: 模型切换
    - CheckpointManager: checkpoint 管理
    """

    def __init__(self, agent_id: str, provider_manager: ProviderManager | None = None):
        super().__init__(agent_id)

        self._agent: Any = None
        self._checkpointer: Any = None
        self._store: Any = None
        self._adapter_factory = LLMResponseAdapterFactory()
        self._model_name: str | None = None
        self._provider_manager = provider_manager

        # 子模块
        self._agent_mgr: AgentLifecycleManager | None = None
        self._model_switcher: ModelSwitchManager | None = None
        self._checkpoint_mgr: CheckpointManager | None = None

        # 运行时状态
        self._backend: Any = None

        # SessionManager（由外部注入或延迟创建）
        self._session_mgr: Any | None = None

        logger.debug(f"[DeepAgentRuntime] Created: {agent_id}")

    @property
    def agent_type(self) -> str:
        return "deep"

    @property
    def session_manager(self) -> Any | None:
        """获取 SessionManager 实例"""
        # 返回父类的 session_manager（通过 ManagerAwareRuntime 继承）
        return getattr(self, "_session_mgr", None)

    async def _do_initialize(self) -> None:
        """初始化 Runtime"""
        # 必须提供 ProviderManager
        if not self._provider_manager:
            raise RuntimeError(
                "ProviderManager is required for DeepAgentRuntime. "
                "All model configuration must be provided through ProviderManager."
            )

        config = self._config
        if config is None:
            raise ValueError("Config not set")

        if isinstance(config, dict):
            config = DeepAgentConfig.model_validate(config)
        elif isinstance(config, EngineConfig):
            config = self._convert_engine_config(config)

        self._config = config

        # 初始化子模块
        self._agent_mgr = AgentLifecycleManager(self._agent_id, config)

        try:
            from langgraph.checkpoint.memory import MemorySaver
            from langgraph.store.memory import InMemoryStore
        except ImportError as e:
            raise ImportError("Required packages missing. Install: pip install langgraph") from e

        self._checkpointer = MemorySaver()
        self._store = InMemoryStore()

        # 加载技能和设置 backend
        self._agent_mgr.load_skill_scripts()
        self._backend = self._create_backend()

        # 创建模型和 Agent
        model = await self._create_model()
        self._agent = self._build_agent(model)

        # 初始化其他子模块
        self._model_switcher = ModelSwitchManager(self)
        self._checkpoint_mgr = CheckpointManager(self._checkpointer)

        logger.info(f"[DeepAgentRuntime] Initialized: {self._agent_id}")

    def _convert_engine_config(self, engine_config: EngineConfig) -> DeepAgentConfig:
        """转换 EngineConfig 到 DeepAgentConfig"""
        config_dict = engine_config.model_dump()

        skills_value = config_dict.get("skills", [])
        if isinstance(skills_value, dict) and skills_value.get("skills_dir"):
            import os as os_module

            skills_dir = skills_value["skills_dir"]
            skills_value = (
                [
                    d
                    for d in os_module.listdir(skills_dir)
                    if os_module.path.isdir(os_module.path.join(skills_dir, d))
                ]
                if os_module.path.exists(skills_dir)
                else []
            )

        # 从 ProviderManager 获取模型名称
        if not self._provider_manager:
            raise RuntimeError("ProviderManager is required")
        model = self._provider_manager.active_model

        return DeepAgentConfig(
            name=config_dict.get("name", self._agent_id),
            model=model,
            system=config_dict.get("system", ""),
            system_prompt=config_dict.get("system_prompt", ""),
            skills=skills_value if isinstance(skills_value, list) else [],
            subagents=config_dict.get("subagents", []),
            interrupt_on=config_dict.get("interrupt_on", {}),
        )

    def _create_backend(self) -> Any:
        """创建 backend"""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        skills_dir = project_root / "skills"

        # 默认使用本地 shell backend
        # 注：sandbox 模式应通过 ProviderManager 配置传递
        from .deep.services.windows_shell_backend import WindowsShellBackend

        backend = WindowsShellBackend(root_dir=str(skills_dir), virtual_mode=True, inherit_env=True)
        logger.info("[DeepAgentRuntime] Using local shell backend")

        return backend

    async def _create_model(self) -> Any:
        """创建模型实例 - 必须通过 ProviderManager"""
        if not self._provider_manager:
            raise RuntimeError(
                "ProviderManager is required for creating model instance. "
                "All model configuration must be provided through ProviderManager."
            )

        model_config = self._provider_manager.get_model_config()
        return await self._provider_manager.create_model_instance(model_config.model)

    def _build_agent(self, model: Any) -> Any:
        """构建 Agent"""
        from langchain_core.tools import StructuredTool

        adapted_tools = [
            StructuredTool.from_function(
                func=tool_info.handler,
                name=name,
                description=tool_info.description,
            )
            for name, tool_info in self._agent_mgr.tools.items()
        ]

        base_prompt = self._config.system or self._config.system_prompt or ""
        path_hint = (
            "\n\n## Environment\n"
            "You run inside a Linux Docker container. "
            "Use Linux commands (ls, cat, grep, cd). "
            "Python is `python` or `python3`. Node/npm are available. "
            "File tools use absolute paths under `/workspace/skills`. "
            "Shell commands use relative paths.\n\n"
            "## Self-Healing\n"
            "If any Python package is missing, fix it with `execute('pip install <package>')`. "
            "Same for Node: `execute('npm install <package>')`.\n\n"
            "## SQL\n"
            "Always use the `run_sql_query` tool directly with the SQL string."
        )
        system_prompt = base_prompt + path_hint if base_prompt else path_hint

        builder = (
            AgentBuilder()
            .with_name(self._config.name or self._agent_id)
            .with_model(model)
            .with_tools(adapted_tools)
            .with_system_prompt(system_prompt)
            .with_backend(self._backend)
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

        return builder.build()

    async def send_message(
        self,
        dialog_id: str,
        message: str,
        stream: bool = True,
        message_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """发送消息，返回流式事件"""
        if self._agent is None:
            raise RuntimeError("DeepAgentRuntime not initialized")

        # 检查模型切换
        await self._model_switcher.check_and_switch(dialog_id)

        # 获取或创建会话
        session_mgr = self.session_manager
        if session_mgr is not None:
            session = await session_mgr.get_session(dialog_id)
            if session is None:
                await session_mgr.create_session(dialog_id, title=message[:50])
            await session_mgr.start_ai_response(dialog_id, message_id or f"msg_{id(message)}")

        # 构建消息
        from backend.domain.models.events.event_models import UserMessageModel

        user_msg = UserMessageModel(role="user", content=message)
        messages = [user_msg.model_dump()]
        messages = self._merge_system_messages(messages)

        # 配置 - 使用默认 recursion_limit
        config = {"configurable": {"thread_id": dialog_id}, "recursion_limit": 100}

        # 处理流
        handler = EventStreamHandler(dialog_id, message_id or f"msg_{id(message)}")

        try:
            async for raw_event in self._agent.astream(
                {"messages": messages}, config, stream_mode=["messages"]
            ):
                for event in handler._process_raw_event(raw_event):
                    yield event

            # 完成
            if session_mgr is not None and handler.state.accumulated_content:
                await session_mgr.complete_ai_response(
                    dialog_id,
                    message_id or f"msg_{id(message)}",
                    handler.state.accumulated_content,
                    metadata={
                        "model": handler.state.actual_model_name or self._model_name or "unknown",
                        "reasoning_content": handler.state.accumulated_reasoning,
                    },
                )

            # Checkpoint 快照
            if self._checkpoint_mgr:
                checkpoint_data = self._checkpoint_mgr.get_checkpoint_snapshot(dialog_id)
                self._checkpoint_mgr.save_snapshot(checkpoint_data)

            yield handler.build_completion_event(
                handler.state.actual_model_name or self._model_name or "unknown",
                self._adapter_factory.detect_provider(
                    handler.state.actual_model_name or self._model_name or ""
                )
                or "unknown",
            )

        except Exception as e:
            logger.exception(f"[DeepAgentRuntime] Error: {e}")
            yield AgentEvent(type="error", data=str(e))

    def _merge_system_messages(self, messages: list) -> list:
        """合并 system 消息"""
        system_parts = []
        others = []
        for msg in messages:
            role = msg.get("role") or msg.get("type", "")
            if role == "system":
                content = msg.get("content", "")
                if isinstance(content, str):
                    system_parts.append(content)
                elif isinstance(content, list):
                    system_parts.append(self._extract_text_content(msg))
                else:
                    system_parts.append(str(content))
            else:
                others.append(msg)

        if system_parts:
            return [{"role": "system", "content": "\n\n".join(system_parts)}] + others
        return others

    @staticmethod
    def _extract_text_content(msg: dict) -> str:
        """提取文本内容"""
        raw = msg.get("data", {}).get("content", "") if isinstance(msg, dict) else ""
        if isinstance(raw, str):
            return raw
        if isinstance(raw, list):
            parts = []
            for block in raw:
                if isinstance(block, dict):
                    if "text" in block:
                        parts.append(str(block["text"]))
                    elif "content" in block:
                        parts.append(str(block["content"]))
                elif isinstance(block, str):
                    parts.append(block)
            return "".join(parts)
        return str(raw)

    async def _do_shutdown(self) -> None:
        """清理资源"""
        logger.info(f"[DeepAgentRuntime] Stopped: {self._agent_id}")

    async def stop(self, dialog_id: str | None = None) -> None:
        """停止 Agent"""
        if self._agent is not None and hasattr(self._agent, "stop"):
            await self._agent.stop()
        logger.info(f"[DeepAgentRuntime] Stopped: {self._agent_id}")

    def register_tool(
        self, name: str, handler: Any, description: str, parameters_schema: dict | None = None
    ) -> None:
        """注册工具"""
        if self._agent_mgr:
            self._agent_mgr.register_tool(name, handler, description, parameters_schema)
        else:
            self._tools[name] = ToolCache(
                handler=handler,
                description=description,
                parameters_schema=parameters_schema or {},
            )

    def unregister_tool(self, name: str) -> None:
        """注销工具"""
        if self._agent_mgr:
            self._agent_mgr.unregister_tool(name)
        else:
            self._tools.pop(name, None)


__all__ = ["DeepAgentRuntime"]
