"""Deep Agent Runtime - 基于 deep-agents 框架的 Runtime 实现

使用 agents 模块的灵活构建器创建 Agent，
并通过适配器模式包装为 AgentRuntime 接口。
"""

from typing import AsyncIterator, Any, Optional, Callable

from loguru import logger
from pydantic import BaseModel

from backend.infrastructure.runtime.runtime import AbstractAgentRuntime, ToolCache
from backend.domain.models.dialog.dialog import Dialog
from backend.domain.models.shared.config import EngineConfig
from backend.domain.models.shared import AgentEvent
from backend.domain.models.events.event_models import UserMessageModel
from .services.config_adapter import DeepAgentConfig
from .services.logging_mixin import DeepLoggingMixin
from langchain_anthropic import ChatAnthropic

# 导入新的灵活构建器
from .agents import AgentBuilder, MiddlewareStack


class DeepAgentRuntime(AbstractAgentRuntime[DeepAgentConfig], DeepLoggingMixin):
    """
    Deep Agent Runtime 实现

    基于 deep-agents 框架，提供高级功能：
    - 任务规划 (TodoListMiddleware)
    - 文件系统操作 (FilesystemMiddleware)
    - 子代理 (SubAgentMiddleware)
    - 持久化记忆 (Store + checkpointer)
    - Human-in-the-loop (interrupt)

    日志输出：
    - logs/deep/deep_messages.log: AIMessage 级别日志（异步队列）
    - logs/deep/deep_updates.log: 节点更新日志（异步队列）
    - logs/deep/deep_values.log: 完整状态日志（异步队列）
    """

    def __init__(self, agent_id: str):
        # 先调用 DeepLoggingMixin 的 __init__ 初始化日志缓冲区
        DeepLoggingMixin.__init__(self)
        super().__init__(agent_id)

        self._agent: Any = None  # deep agent 实例
        self._checkpointer: Any = None
        self._store: Any = None

        logger.debug(f"[DeepAgentRuntime] Created: {agent_id}")

    @property
    def agent_type(self) -> str:
        return "deep"

    @property
    def session_manager(self):
        return getattr(self, "_session_mgr", None)

    def set_session_manager(self, mgr):
        self._session_mgr = mgr

    async def _do_initialize(self) -> None:
        """初始化 Runtime 和 Deep Agent"""
        import os
        from pathlib import Path
        from dotenv import load_dotenv

        # 安全网：确保加载项目根目录的 .env（覆盖已有环境变量）
        env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)

        # 清除错误的中文占位符 token，避免 anthropic client 将其加入 HTTP header 导致编码错误
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

        # 使用 self._config（已由基类 initialize 设置）
        config = self._config
        if config is None:
            raise ValueError("Config not set. Call initialize() first.")

        # 统一转换为 DeepAgentConfig
        if isinstance(config, dict):
            self._config = DeepAgentConfig.model_validate(config)
        elif isinstance(config, EngineConfig):
            config_dict = config.model_dump()
            # skills 可能是 dict (来自 EngineConfig.skills) 或 list
            skills_value = config_dict.get("skills", [])
            if isinstance(skills_value, dict):
                # 从 skills_dir 提取 skill ID 列表
                skills_list = []
                if skills_value.get("skills_dir"):
                    import os
                    skills_dir = skills_value["skills_dir"]
                    if os.path.exists(skills_dir):
                        skills_list = [d for d in os.listdir(skills_dir)
                                       if os.path.isdir(os.path.join(skills_dir, d))]
                skills_value = skills_list

            # 获取模型名称 - 优先从环境变量，然后配置，最后默认值
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
        # 如果已经是 DeepAgentConfig，保持不变

        # 确保 _config 不是 None（类型检查器需要这个确认）
        if self._config is None:
            raise ValueError("Config conversion failed")

        try:
            from langgraph.checkpoint.memory import MemorySaver
            from langgraph.store.memory import InMemoryStore
            from .services.docker_sandbox_backend import create_sandbox_backend
        except ImportError as e:
            raise ImportError(
                "Required packages are missing for DeepAgentRuntime. "
                "Install with: pip install deepagents langgraph"
            ) from e

        # 加载技能脚本中的工具
        self._load_skill_scripts()

        # 配置 checkpointer 和 store
        self._checkpointer = MemorySaver()
        self._store = InMemoryStore()

        # 配置 backend - 使用 skills 目录作为根目录
        # 使用 virtual_mode=True 让 /finance/SKILL.md 映射到 skills/finance/SKILL.md
        # 默认通过 AGENT_SANDBOX=docker 启用 Docker Sandbox；未启用或 Docker 不可用时自动降级到 LocalShellBackend
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        skills_dir = project_root / "skills"
        agent_sandbox = os.getenv("AGENT_SANDBOX", "local").strip().lower()
        if agent_sandbox == "docker":
            backend = create_sandbox_backend(root_dir=str(skills_dir), virtual_mode=True, inherit_env=True)
            logger.info(f"[DeepAgentRuntime] Using sandbox backend for skills_dir={skills_dir}")
        else:
            from .services.windows_shell_backend import WindowsShellBackend
            backend = WindowsShellBackend(root_dir=str(skills_dir), virtual_mode=True, inherit_env=True)
            logger.info(f"[DeepAgentRuntime] Using local shell backend for skills_dir={skills_dir}")

        # 若使用 Docker Sandbox，将依赖特定运行环境的工具代理到容器中执行
        if agent_sandbox == "docker":
            self._proxy_sandbox_tools(backend)

        # 转换工具格式（必须在 backend 创建及代理包装之后）
        from langchain_core.tools import StructuredTool
        adapted_tools = [
            StructuredTool.from_function(
                func=tool_info.handler,
                name=name,
                description=tool_info.description,
            )
            for name, tool_info in self._tools.items()
        ]

        # 解析模型：字符串模型若无法被 deepagents 自动推断 provider，则手动构造实例
        model_name = os.getenv("MODEL_ID", "").strip() or "kimi-k2-coding"
        base_url = os.getenv("ANTHROPIC_BASE_URL", "").strip() or "https://api.kimi.com/coding/"
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

        logger.info(
            f"[DeepAgentRuntime] Model config: model_name={model_name}, "
            f"base_url={base_url}, api_key_set={api_key}"
        )

        model = ChatAnthropic(
            model=model_name,
            api_key=api_key,
            anthropic_api_url=base_url,
            temperature=0.7,
        )

        # 构建系统提示词，告知 LLM 它在容器环境中，应自治解决依赖与路径问题
        base_prompt = self._config.system or self._config.system_prompt or ""
        path_hint = (
            "\n\n## Environment\n"
            "You run inside a Linux Docker container. "
            "Use Linux commands (ls, cat, grep, cd). "
            "Python is `python` or `python3`. Node/npm are available. "
            "File tools use absolute paths under `/workspace/skills` (e.g. `/finance/SKILL.md`). "
            "Shell commands use relative paths (e.g. `cd finance/scripts`).\n\n"
            "## Self-Healing\n"
            "If any Python package is missing, fix it yourself with `execute('pip install <package>')` then retry. "
            "Same for Node: `execute('npm install <package>')`. Installed packages persist in this container.\n\n"
            "## SQL\n"
            "Always use the `run_sql_query` tool directly with the SQL string."
        )
        system_prompt = base_prompt + path_hint if base_prompt else path_hint

        # 使用新的灵活 AgentBuilder 创建 Agent
        # 这种方式允许更灵活的中间件配置
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
            .with_claude_compression(
                level="standard",
                enable_session_memory=True,  # 启用 Backend 存储
            )
            .with_prompt_caching()
        )

        # 如果有 interrupt_on 配置，添加人工介入中间件
        if self._config.interrupt_on:
            builder.with_human_in_the_loop(interrupt_on=self._config.interrupt_on)

        # 构建 Agent
        self._agent = builder.build()

        logger.info(f"[DeepAgentRuntime] Initialized: {self._agent_id} (using flexible AgentBuilder)")

    @staticmethod
    @staticmethod
    def _extract_text_content(msg: dict) -> str:
        """从 message dict 中安全提取文本内容，兼容 str / list / dict"""
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
    def _merge_system_messages(cls, messages: list[dict]) -> list[dict]:
        """合并所有 system 消息到列表最前面，满足 Anthropic 格式要求。"""
        system_parts: list[str] = []
        others: list[dict] = []
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
            merged_system = {"role": "system", "content": "\n\n".join(system_parts)}
            return [merged_system] + others
        return others

    def _load_skill_scripts(self) -> None:
        """加载技能脚本中的工具（如 run_sql_query）"""
        import sys
        import importlib.util
        from pathlib import Path
        from backend.infrastructure.tools.toolkit import scan_tools

        project_root = Path(__file__).resolve().parent.parent.parent.parent
        skills_dir = project_root / "skills"

        if not skills_dir.exists():
            logger.warning("[DeepAgentRuntime] Skills directory not found: %s", skills_dir)
            return

        tool_count = 0
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            
            scripts_dir = skill_dir / "scripts"
            if not scripts_dir.exists():
                continue

            # 将 scripts 目录添加到 sys.path 以支持相对导入
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))

            for py_file in sorted(scripts_dir.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                
                module_name = f"skills.{skill_dir.name}.{py_file.stem}"
                try:
                    spec = importlib.util.spec_from_file_location(module_name, py_file)
                    if spec is None or spec.loader is None:
                        continue
                    
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    for tool_item in scan_tools(module):
                        self._tools[tool_item["name"]] = ToolCache(
                            handler=tool_item["handler"],
                            description=tool_item["description"],
                            parameters_schema=tool_item.get("parameters", {}),
                        )
                        tool_count += 1
                        logger.info("[DeepAgentRuntime] Loaded skill tool: %s", tool_item["name"])
                except Exception as e:
                    # 记录警告但继续加载其他脚本
                    logger.warning("[DeepAgentRuntime] Failed to load skill script %s: %s", py_file, e)

        logger.info("[DeepAgentRuntime] Loaded %d skill tools", tool_count)

    def _proxy_sandbox_tools(self, backend: Any) -> None:
        """将需要特定运行环境的工具代理到 sandbox 容器中执行。

        这样自定义 Python 工具（如 run_sql_query）不再受限于宿主机 .venv-new
        的依赖环境，而是在容器内统一执行。
        """
        import base64
        import json

        if "run_sql_query" in self._tools:
            original = self._tools["run_sql_query"]

            def proxy_run_sql_query(sql: str, limit: int = 200) -> str:
                # 使用 base64 内嵌 Python 脚本，彻底避免 Windows + Docker + shlex 引号地狱
                payload = json.dumps({"sql": sql, "limit": limit})
                b64 = base64.b64encode(payload.encode()).decode()
                cmd = (
                    f"python -c \"import base64, json, sys; "
                    f"p=json.loads(base64.b64decode('{b64}').decode()); "
                    f"sys.path.insert(0, 'finance/scripts'); "
                    f"from sql_query import run_sql_query; "
                    f"print(run_sql_query(**p))\""
                )
                result = backend.execute(cmd)
                return result.output

            self._tools["run_sql_query"] = ToolCache(
                handler=proxy_run_sql_query,
                description=original.description,
                parameters_schema=original.parameters_schema,
            )
            logger.info("[DeepAgentRuntime] Proxied run_sql_query to sandbox")

    async def _do_shutdown(self) -> None:
        """子类实现: 特定清理逻辑"""
        # Deep Agent 无需特殊清理
        pass

    async def send_message(  # type: ignore[override,misc]
        self,
        dialog_id: str,
        message: str,
        stream: bool = True,
        message_id: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]:
        """
        发送消息，返回流式事件

        使用 stream_mode="messages" 实现真正的 token 级流式输出，
        同时与 SessionManager 集成进行对话历史管理。

        所有日志写入使用异步队列（enqueue=True），不影响主流程性能。
        """
        if self._agent is None:
            raise RuntimeError("DeepAgentRuntime not initialized. Call initialize() first.")

        # 获取或创建会话
        session_mgr = self.session_manager
        if session_mgr is not None:
            # 检查会话是否存在，不存在则创建
            session = await session_mgr.get_session(dialog_id)
            if session is None:
                await session_mgr.create_session(dialog_id, title=message[:50])
            # 添加用户消息到 SessionManager
            await session_mgr.add_user_message(dialog_id, message)
            # 从 SessionManager 获取对话历史
            history_messages = await session_mgr.get_messages(dialog_id)
            # 转换为 LangChain 消息格式
            messages = []
            for msg in history_messages:
                if hasattr(msg, 'model_dump'):
                    messages.append(msg.model_dump())
                elif hasattr(msg, 'content'):
                    messages.append({
                        "role": getattr(msg, 'type', 'unknown'),
                        "content": msg.content
                    })
                else:
                    messages.append(msg)
            # 标记 AI 响应开始
            ai_message_id = message_id or f"msg_{id(message)}"
            await session_mgr.start_ai_response(dialog_id, ai_message_id)
        else:
            # 回退：直接使用当前消息
            user_msg = UserMessageModel(role="user", content=message)
            messages = [user_msg.model_dump() if isinstance(user_msg, BaseModel) else {"role": "user", "content": message}]
            ai_message_id = message_id or f"msg_{id(message)}"

        # Anthropic 要求所有 system 消息必须连续出现在最开头，不能夹杂在对话中间。
        # 中间件（如 TodoListMiddleware、SkillsMiddleware）可能在历史消息中插入了 system 消息，
        # 因此需要在传给模型前把它们合并到第一条。
        messages = self._merge_system_messages(messages)

        # 配置 thread_id 用于持久化，同时支持通过环境变量调整 recursion_limit
        import os
        recursion_limit = int(os.getenv("AGENT_RECURSION_LIMIT", "100").strip())
        config = {"configurable": {"thread_id": dialog_id}, "recursion_limit": recursion_limit}

        # 记录用户消息到三种日志
        self._msg_logger.debug("User message: {}", message[:200])
        self._update_logger.debug("Start conversation: dialog_id={}", dialog_id)
        self._value_logger.debug("Initial state: dialog_id={}, message_count={}", dialog_id, len(messages))

        # 用于累积流式内容
        accumulated_content = ""
        accumulated_reasoning = ""
        last_message_id = None

        try:
            # 使用 stream_mode="messages" 获取 token 级增量数据
            self._update_logger.info("Starting astream for dialog={}", dialog_id)
            async for raw_event in self._agent.astream(
                {"messages": messages},
                config,
                stream_mode=["messages"]
            ):
                import json
                from datetime import datetime
                
                # 记录原始事件到 JSONL（处理不可序列化的对象）
                try:
                    with open("logs/deep/raw_event.jsonl", "a", encoding="utf-8") as f:
                        json_str = json.dumps(raw_event, ensure_ascii=False, default=str)
                        f.write(json_str + chr(10))
                except Exception as log_e:
                    self._update_logger.debug("Failed to log raw event: {}", log_e)

                # 处理流式事件并转发给 SessionManager
                # 提取内容增量
                delta_content = ""
                delta_reasoning = ""
                
                # 处理不同格式的 raw_event
                if isinstance(raw_event, tuple) and len(raw_event) >= 2:
                    # (stream_mode, (message_chunk, metadata)) 格式
                    msg_chunk = raw_event[1]
                    if isinstance(msg_chunk, tuple):
                        msg_chunk = msg_chunk[0]

                    # 仅向前端广播 ToolMessage（不写入 SessionManager）
                    if getattr(msg_chunk, 'type', None) == 'tool':
                        tool_call_id = getattr(msg_chunk, 'tool_call_id', 'unknown')
                        tool_content = getattr(msg_chunk, 'content', '')
                        tool_name = getattr(msg_chunk, 'name', 'unknown')
                        yield AgentEvent(
                            type="tool_result",
                            data={
                                "tool_name": tool_name,
                                "tool_call_id": tool_call_id,
                                "result": str(tool_content),
                            },
                            metadata={"tool_call_id": tool_call_id}
                        )
                        try:
                            from pathlib import Path
                            _tool_log_path = Path(r"D:\learn-claude-code-my\logs\deep\tool_results.jsonl")
                            _tool_log_path.parent.mkdir(parents=True, exist_ok=True)
                            with _tool_log_path.open("a", encoding="utf-8") as f:
                                f.write(json.dumps({
                                    "timestamp": datetime.now().isoformat(),
                                    "dialog_id": dialog_id,
                                    "type": "tool_result",
                                    "tool_call_id": tool_call_id,
                                    "tool_name": tool_name,
                                    "result": str(tool_content)[:2000],
                                }, ensure_ascii=False, default=str) + "\n")
                        except Exception:
                            pass
                        continue

                    # 仅向前端广播 assistant 的 tool_calls
                    if getattr(msg_chunk, 'type', None) in ('ai', 'assistant'):
                        tool_calls = getattr(msg_chunk, 'tool_calls', None) or []
                        if tool_calls:
                            for tc in tool_calls:
                                tc_id = tc.get('id', 'call_0')
                                tc_name = tc.get('name', 'unknown')
                                tc_args = tc.get('args', {})
                                if isinstance(tc_args, str):
                                    try:
                                        import json
                                        tc_args = json.loads(tc_args)
                                    except Exception:
                                        tc_args = {"raw": tc_args}
                                yield AgentEvent(
                                    type="tool_call",
                                    data={
                                        "message_id": message_id or "unknown",
                                        "tool_call": {
                                            "id": tc_id,
                                            "name": tc_name,
                                            "arguments": tc_args,
                                            "status": "pending",
                                        },
                                    },
                                )
                                try:
                                    from pathlib import Path
                                    _tool_log_path = Path(r"D:\learn-claude-code-my\logs\deep\tool_results.jsonl")
                                    _tool_log_path.parent.mkdir(parents=True, exist_ok=True)
                                    with _tool_log_path.open("a", encoding="utf-8") as f:
                                        f.write(json.dumps({
                                            "timestamp": datetime.now().isoformat(),
                                            "dialog_id": dialog_id,
                                            "type": "tool_call",
                                            "tool_call": {
                                                "id": tc_id,
                                                "name": tc_name,
                                                "arguments": tc_args,
                                                "status": "pending",
                                            },
                                        }, ensure_ascii=False, default=str) + "\n")
                                except Exception:
                                    pass

                    if hasattr(msg_chunk, 'content') and msg_chunk.content:
                        content = msg_chunk.content
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get('type') == 'text':
                                    delta_content += block.get('text', '')
                                elif isinstance(block, str):
                                    delta_content += block
                        else:
                            delta_content = str(content)

                    # 检查推理内容
                    if hasattr(msg_chunk, 'additional_kwargs'):
                        reasoning = msg_chunk.additional_kwargs.get('reasoning_content', '')
                        if reasoning:
                            delta_reasoning = str(reasoning)
                
                # 转发 delta 到 SessionManager
                if session_mgr is not None:
                    if delta_content:
                        await session_mgr.emit_delta(dialog_id, delta_content, ai_message_id)
                    if delta_reasoning:
                        await session_mgr.emit_reasoning_delta(dialog_id, delta_reasoning, ai_message_id)
                
                # 累积内容并产出事件给调用者
                if delta_content:
                    accumulated_content += delta_content
                    yield AgentEvent(
                        type="text_delta",
                        data=delta_content,
                        metadata={"accumulated_length": len(accumulated_content)}
                    )
                
                if delta_reasoning:
                    accumulated_reasoning += delta_reasoning
                    yield AgentEvent(
                        type="reasoning_delta",
                        data=delta_reasoning,
                        metadata={"accumulated_length": len(accumulated_reasoning)}
                    )

            # 流结束，保存完整 AI 响应到 SessionManager
            if session_mgr is not None:
                final_content = accumulated_content
                if final_content:
                    await session_mgr.complete_ai_response(
                        dialog_id, 
                        ai_message_id, 
                        final_content,
                        metadata={"reasoning_content": accumulated_reasoning} if accumulated_reasoning else {}
                    )
                    self._update_logger.info(
                        "AI response completed and saved to session: dialog_id={}, content_len={}",
                        dialog_id, len(final_content)
                    )
            
            # 发送完成事件给调用者
            if accumulated_content:
                yield AgentEvent(
                    type="text_complete",
                    data=accumulated_content,
                    metadata={"reasoning_content": accumulated_reasoning} if accumulated_reasoning else {}
                )

        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            logger.exception(f"[DeepAgentRuntime] Error in send_message: {e}")
            self._msg_logger.error("Error: {}", error_detail)
            self._update_logger.error("Error: {}", str(e))
            self._value_logger.error("Error: {}", str(e))
            yield AgentEvent(type="error", data=str(e))

    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str,
        parameters_schema: Optional[dict[str, Any]] = None
    ) -> None:
        """注册工具（缓存，在 initialize 时转换）"""
        self._tools[name] = ToolCache(
            handler=handler,
            description=description,
            parameters_schema=parameters_schema or {},
        )
        logger.debug(f"[DeepAgentRuntime] Registered tool (cached): {name}")

        # 如果已经初始化，需要重新初始化以应用新工具
        if self._agent is not None:
            logger.warning(
                f"[DeepAgentRuntime] Tool {name} registered after initialization. "
                "Call initialize() again to apply changes."
            )

    def unregister_tool(self, name: str) -> None:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            logger.debug(f"[DeepAgentRuntime] Unregistered tool: {name}")

    async def stop(self, dialog_id: Optional[str] = None) -> None:
        """停止 Agent"""
        # Deep Agent 的停止逻辑
        if self._agent is not None:
            # 如果有停止方法则调用
            if hasattr(self._agent, 'stop'):
                await self._agent.stop()

        # 记录停止日志
        self._msg_logger.debug("Agent stopped: dialog_id={}", dialog_id or "all")
        self._update_logger.debug("Agent stopped: dialog_id={}", dialog_id or "all")
        self._value_logger.debug("Agent stopped: dialog_id={}", dialog_id or "all")

        logger.info(f"[DeepAgentRuntime] Stopped: {self._agent_id}")


__all__ = ["DeepAgentRuntime"]