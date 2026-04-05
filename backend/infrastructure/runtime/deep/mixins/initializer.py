"""Deep Initializer Mixin - 初始化功能

从 deep_legacy.py 提取的初始化逻辑。
"""

import os
from pathlib import Path
from typing import Any, Optional
from loguru import logger

from backend.infrastructure.services import ProviderManager
from backend.domain.models.shared.config import EngineConfig
from backend.infrastructure.runtime.deep.services.config_adapter import DeepAgentConfig


class DeepInitializerMixin:
    """初始化 Mixin"""

    _config: Optional[DeepAgentConfig]
    _agent_id: str
    _provider_manager: Optional[ProviderManager]
    _tools: dict[str, Any]
    _checkpointer: Any
    _store: Any
    _agent: Any
    _model_name: Optional[str]

    async def _do_initialize(self) -> None:
        """初始化 Runtime 和 Deep Agent"""
        from dotenv import load_dotenv

        # 初始化统一日志记录器（必须在其他操作之前）
        await self._init_unified_loggers()

        # 安全网：确保加载项目根目录的 .env（覆盖已有环境变量）
        env_path = Path(__file__).resolve().parent.parent.parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)

        # 清除错误的中文占位符 token
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

        config = self._config
        if config is None:
            raise ValueError("Config not set. Call initialize() first.")

        # 统一转换为 DeepAgentConfig
        if isinstance(config, dict):
            self._config = DeepAgentConfig.model_validate(config)
        elif isinstance(config, EngineConfig):
            config_dict = config.model_dump()
            skills_value = config_dict.get("skills", [])
            if isinstance(skills_value, dict):
                skills_list = []
                if skills_value.get("skills_dir"):
                    skills_dir = skills_value["skills_dir"]
                    if os.path.exists(skills_dir):
                        skills_list = [d for d in os.listdir(skills_dir)
                                       if os.path.isdir(os.path.join(skills_dir, d))]
                skills_value = skills_list

            if self._provider_manager:
                model = self._provider_manager.active_model
            else:
                model = os.getenv("MODEL_ID", "").strip()
                if not model:
                    model = config_dict.get("provider", {}).get("model", "claude-sonnet-4-6")

            self._config = DeepAgentConfig(
                name=config_dict.get("name", self._agent_id),
                model=model,
                system=config_dict.get("system", ""),
                system_prompt=config_dict.get("system_prompt", ""),
                skills=skills_value if isinstance(skills_value, list) else [],
                subagents=config_dict.get("subagents", []),
                interrupt_on=config_dict.get("interrupt_on", {}),
            )

        if self._config is None:
            raise ValueError("Config conversion failed")

        try:
            from langgraph.checkpoint.memory import MemorySaver
            from langgraph.store.memory import InMemoryStore
            from backend.infrastructure.runtime.deep.services.docker_sandbox_backend import create_sandbox_backend
        except ImportError as e:
            raise ImportError(
                "Required packages are missing for DeepAgentRuntime. "
                "Install with: pip install deepagents langgraph"
            ) from e

        # 加载技能脚本
        self._load_skill_scripts()

        # 配置 checkpointer 和 store
        self._checkpointer = MemorySaver()
        self._store = InMemoryStore()

        # 配置 backend
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
        skills_dir = project_root / "skills"
        agent_sandbox = os.getenv("AGENT_SANDBOX", "local").strip().lower()
        if agent_sandbox == "docker":
            backend = create_sandbox_backend(root_dir=str(skills_dir), virtual_mode=True, inherit_env=True)
            logger.info(f"[DeepAgentRuntime] Using sandbox backend for skills_dir={skills_dir}")
        else:
            from backend.infrastructure.runtime.deep.services.windows_shell_backend import WindowsShellBackend
            backend = WindowsShellBackend(root_dir=str(skills_dir), virtual_mode=True, inherit_env=True)
            logger.info(f"[DeepAgentRuntime] Using local shell backend for skills_dir={skills_dir}")

        if agent_sandbox == "docker":
            self._proxy_sandbox_tools(backend)

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

        # 创建模型实例
        if self._provider_manager:
            model_config = self._provider_manager.get_model_config()
            model_name = model_config.model
            logger.info(
                f"[DeepAgentRuntime] Model config: model_name={model_name}, "
                f"api_key_set={'yes' if model_config.api_key else 'no'}"
            )
            try:
                model = await self._provider_manager.create_model_instance(model_name)
                logger.info(f"[DeepAgentRuntime] Created model via ProviderManager: {model_name}")
            except Exception as e:
                logger.error(f"[DeepAgentRuntime] Failed to create model: {e}")
                raise RuntimeError(f"Failed to create model: {e}")
        else:
            model_name = os.getenv("MODEL_ID", "claude-sonnet-4-6")
            api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or ""
            base_url = os.getenv("ANTHROPIC_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or ""
            logger.warning(f"[DeepAgentRuntime] No ProviderManager, using direct creation")
            try:
                from langchain_community.chat_models import ChatLiteLLM
                model = ChatLiteLLM(
                    model=model_name, api_key=api_key,
                    api_base=base_url if base_url else None, temperature=0.7,
                )
            except Exception as e:
                logger.warning(f"[DeepAgentRuntime] ChatLiteLLM failed: {e}")
                from langchain_anthropic import ChatAnthropic
                model = ChatAnthropic(
                    model=model_name, api_key=api_key,
                    anthropic_api_url=base_url, temperature=0.7,
                )

        self._model_name = model_name

        # 构建系统提示词
        base_prompt = self._config.system or self._config.system_prompt or ""
        path_hint = (
            "\n\n## Environment\n"
            "You run inside a Linux Docker container. "
            "Use Linux commands (ls, cat, grep, cd). "
            "Python is `python` or `python3`. Node/npm are available. "
            "File tools use absolute paths under `/workspace/skills`.\n\n"
            "## Self-Healing\n"
            "If any Python package is missing, fix it with `execute('pip install <package>')`.\n\n"
            "## SQL\n"
            "Always use the `run_sql_query` tool directly with the SQL string."
        )
        system_prompt = base_prompt + path_hint if base_prompt else path_hint

        # 使用 AgentBuilder 创建 Agent
        from ..agents import AgentBuilder
        builder = (
            AgentBuilder()
            .with_name(self._config.name or self._agent_id)
            .with_model(model)
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
        logger.info(f"[DeepAgentRuntime] Initialized: {self._agent_id}")

    async def _do_shutdown(self) -> None:
        """子类实现: 特定清理逻辑"""
        await self._stop_unified_loggers()

    @staticmethod
    def _extract_text_content(msg: dict[str, Any]) -> str:
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

    @classmethod
    def _merge_system_messages(cls, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                    system_parts.append(cls._extract_text_content(msg))
                else:
                    system_parts.append(str(content))
            else:
                others.append(msg)
        if system_parts:
            return [{"role": "system", "content": "\n\n".join(system_parts)}] + others
        return messages

    # _init_unified_loggers 和 _stop_unified_loggers 由 DeepLoggingMixin 提供
    # 不要在这里实现空方法，否则会覆盖 Mixin 中的实现
