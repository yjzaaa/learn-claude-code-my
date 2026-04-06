"""Deep Initializer Mixin - 初始化功能

从 deep_legacy.py 提取的初始化逻辑。
"""

from pathlib import Path
from typing import Any

from loguru import logger

from backend.domain.models.shared.config import EngineConfig
from backend.infrastructure.runtime.deep.services.config_adapter import DeepAgentConfig
from backend.infrastructure.services import ProviderManager


class DeepInitializerMixin:
    """初始化 Mixin"""

    _config: DeepAgentConfig | None
    _agent_id: str
    _provider_manager: ProviderManager | None
    _tools: dict[str, Any]
    _checkpointer: Any
    _store: Any
    _agent: Any
    _model_name: str | None

    async def _do_initialize(self) -> None:
        """初始化 Runtime 和 Deep Agent"""
        # 初始化统一日志记录器（必须在其他操作之前）
        await self._init_unified_loggers()

        config = self._config
        if config is None:
            raise ValueError("Config not set. Call initialize() first.")

        # 必须有 ProviderManager
        if not self._provider_manager:
            raise RuntimeError(
                "ProviderManager is required. "
                "All model configuration must be provided through ProviderManager."
            )

        # 统一转换为 DeepAgentConfig
        if isinstance(config, dict):
            self._config = DeepAgentConfig.model_validate(config)
        elif isinstance(config, EngineConfig):
            config_dict = config.model_dump()
            skills_value = config_dict.get("skills", [])
            if isinstance(skills_value, dict):
                skills_list = []
                if skills_value.get("skills_dir"):
                    skills_dir = Path(skills_value["skills_dir"])
                    if skills_dir.exists():
                        skills_list = [d.name for d in skills_dir.iterdir() if d.is_dir()]
                skills_value = skills_list

            # 从 ProviderManager 获取模型名称
            model = self._provider_manager.active_model

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

            from backend.infrastructure.runtime.deep.services.universal_shell_backend import (
                create_universal_backend,
            )
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

        # 配置 backend - 使用 UniversalShellBackend 自动处理 Docker/Windows 降级
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
        skills_dir = project_root / "skills"

        backend = create_universal_backend(
            root_dir=str(skills_dir),
            virtual_root="/workspace/skills",
            virtual_mode=True,
            inherit_env=True,
        )
        logger.info(
            f"[DeepAgentRuntime] Using universal backend for skills_dir={skills_dir}, backend_id={backend.id}"
        )

        # 代理 sandbox 工具（如果需要）
        if hasattr(backend, "_use_docker") and backend._use_docker:
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

        # 创建模型实例 - 必须通过 ProviderManager
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

        self._model_name = model_name

        # 加载 skill references 文件内容
        skill_references_content = self._load_skill_references(skills_dir)

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

        # 组合系统提示词：基础提示词 + skill references + 环境提示
        system_prompt_parts = [p for p in [base_prompt, skill_references_content, path_hint] if p]
        system_prompt = "\n\n".join(system_prompt_parts)

        # 使用 AgentBuilder 创建 Agent
        from ..agents import AgentBuilder

        # 构建 skill sources 路径（与 backend 的 virtual_root 一致）
        skill_sources = [f"/workspace/skills/{skill}/" for skill in (self._config.skills or [])]

        builder = (
            AgentBuilder()
            .with_name(self._config.name or self._agent_id)
            .with_model(model)
            .with_tools(adapted_tools)
            .with_system_prompt(system_prompt)
            .with_backend(backend)
            .with_checkpointer(self._checkpointer)
            .with_store(self._store)
            .with_skills(self._config.skills or [], sources=skill_sources)
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
    def _merge_system_messages(cls, messages: list) -> list:
        """合并 system 消息。

        支持 LangChain 消息对象和字典格式。
        """
        from langchain_core.messages import SystemMessage

        system_parts = []
        others = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                # LangChain SystemMessage
                content = msg.content
                if isinstance(content, str):
                    system_parts.append(content)
                else:
                    system_parts.append(str(content))
            elif isinstance(msg, dict):
                # 字典格式
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
            else:
                # 其他 LangChain 消息类型
                msg_type = getattr(msg, "type", "")
                if msg_type == "system":
                    content = getattr(msg, "content", "")
                    if isinstance(content, str):
                        system_parts.append(content)
                    else:
                        system_parts.append(str(content))
                else:
                    others.append(msg)

        if system_parts:
            # 返回合并后的 SystemMessage 对象
            merged_content = "\n\n".join(system_parts)
            return [SystemMessage(content=merged_content)] + others
        return messages

    def _load_skill_references(self, skills_dir: Path) -> str:
        """加载 skill 的 references 文件内容

        读取所有启用的 skill 的 references 目录下的 .md 文件内容，
        并组合成系统提示词的一部分。
        """
        if not self._config or not self._config.skills:
            return ""

        references_parts = []

        for skill_name in self._config.skills:
            skill_dir = skills_dir / skill_name
            if not skill_dir.exists():
                continue

            # 读取 SKILL.md
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    # 移除 YAML frontmatter
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            content = parts[2].strip()
                    references_parts.append(f"## Skill: {skill_name}\n{content}")
                except Exception as e:
                    logger.warning(
                        f"[DeepAgentRuntime] Failed to read SKILL.md for {skill_name}: {e}"
                    )

            # 读取 references 目录下的所有 .md 文件
            references_dir = skill_dir / "references"
            if references_dir.exists() and references_dir.is_dir():
                for md_file in sorted(references_dir.glob("*.md")):
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        references_parts.append(f"### {skill_name}/{md_file.name}\n{content}")
                    except Exception as e:
                        logger.warning(f"[DeepAgentRuntime] Failed to read {md_file}: {e}")

        if references_parts:
            return "## Skills Knowledge Base\n\n" + "\n\n".join(references_parts)

        return ""

    # _init_unified_loggers 和 _stop_unified_loggers 由 DeepLoggingMixin 提供
    # 不要在这里实现空方法，否则会覆盖 Mixin 中的实现
