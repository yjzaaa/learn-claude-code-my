"""Deep Agent Runtime - 基于 deep-agents 框架的 Runtime 实现

使用 agents 模块的灵活构建器创建 Agent，
并通过适配器模式包装为 AgentRuntime 接口。
"""

from typing import AsyncIterator, Any, Optional, Callable

from loguru import logger
from pydantic import BaseModel

from backend.infrastructure.runtime.runtime import AbstractAgentRuntime, ToolCache
from backend.domain.models import Dialog
from backend.domain.models.config import EngineConfig
from backend.domain.models.shared import AgentEvent
from backend.domain.models.event_models import UserMessageModel
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
        super().__init__(agent_id)

        self._agent: Any = None  # deep agent 实例
        self._checkpointer: Any = None
        self._store: Any = None

        # 初始化日志记录器
        self._init_loggers()

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
            from .services.windows_shell_backend import WindowsShellBackend
        except ImportError as e:
            raise ImportError(
                "Required packages are missing for DeepAgentRuntime. "
                "Install with: pip install deepagents langgraph"
            ) from e

        # 加载技能脚本中的工具
        self._load_skill_scripts()

        # 转换工具格式
        adapted_tools = self.adapt_tools(self._tools)

        # 配置 checkpointer 和 store
        self._checkpointer = MemorySaver()
        self._store = InMemoryStore()

        # 配置 backend - 使用 skills 目录作为根目录
        # 使用 virtual_mode=True 让 /finance/SKILL.md 映射到 skills/finance/SKILL.md
        # 使用 WindowsShellBackend 处理 Windows 编码问题
        # inherit_env=True 确保继承系统 PATH 环境变量
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        skills_dir = project_root / "skills"
        backend = WindowsShellBackend(root_dir=str(skills_dir), virtual_mode=True, inherit_env=True)

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

        # 构建系统提示词，添加文件路径和Windows命令使用说明
        base_prompt = self._config.system or self._config.system_prompt or ""
        path_hint = """\n\n## File System Path Guide\nThe filesystem is rooted at the 'skills' folder.\n\n**For file tools (read_file, glob, ls, grep):** Use absolute-style paths with leading slash, e.g., '/finance/SKILL.md' or '/code-review/SKILL.md'.\n\n**For shell commands (execute):** Use relative paths WITHOUT leading slash, e.g., 'finance/scripts/sql_query.py' or 'cd finance && dir'.\n\n## Windows Shell Commands\nThis system runs on Windows. Use Windows-style commands:\n- Use 'dir' instead of 'ls'\n- Use 'cd' with backslashes (e.g., 'cd finance\\scripts')\n- Use 'type' instead of 'cat' to display file contents\n- Use 'findstr' instead of 'grep'\n- Use 'move' instead of 'mv'\n- Use 'copy' instead of 'cp'\n- Use 'del' instead of 'rm'\n- For Python scripts: use 'py script.py' (preferred) or find python path first with 'where python' or 'where py'\n- To use the project's virtual environment: run 'py' or '.venv\Scripts\python.exe' (located at project root, one level above skills folder)\n\n## IMPORTANT: SQL Query Best Practices\nWhen executing SQL queries:\n1. **ALWAYS use the 'run_sql_query' tool directly** instead of shell commands\n2. **NEVER use shell syntax like $(type file) or backticks** - Windows doesn't support this\n3. **Pass SQL as a direct string parameter** to the run_sql_query tool\n4. **For complex multi-line SQL**: Either:\n   - Use the run_sql_query tool with the complete SQL string\n   - Or read the SQL from a file using read_file, then pass it to run_sql_query\n5. **DO NOT use**: 'python finance/scripts/sql_query.py "SELECT ..."' - this is error-prone\n6. **DO use**: Call 'run_sql_query' tool with sql parameter directly"""
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
            # 可选：启用压缩中间件（默认关闭）
            # .with_summarization(trigger=("fraction", 0.85), keep=("fraction", 0.10))
            .with_prompt_caching()
        )

        # 如果有 interrupt_on 配置，添加人工介入中间件
        if self._config.interrupt_on:
            builder.with_human_in_the_loop(interrupt_on=self._config.interrupt_on)

        # 构建 Agent
        self._agent = builder.build()

        logger.info(f"[DeepAgentRuntime] Initialized: {self._agent_id} (using flexible AgentBuilder)")

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

    def adapt_tools(self, tools: dict[str, ToolCache]) -> list:
        """
        将我们的工具格式转换为 LangChain Tool 格式

        Args:
            tools: 我们的工具字典 {name: ToolCache}

        Returns:
            LangChain Tool 列表
        """
        from langchain_core.tools import StructuredTool

        adapted = []

        for name, tool_info in tools.items():
            handler = tool_info.handler
            description = tool_info.description

            # 创建 LangChain Tool
            adapted_tool = StructuredTool.from_function(
                func=handler,
                name=name,
                description=description,
            )
            adapted.append(adapted_tool)

        return adapted

    async def _do_shutdown(self) -> None:
        """子类实现: 特定清理逻辑"""
        # Deep Agent 无需特殊清理
        pass

    async def send_message(  # type: ignore[override,misc]
        self,
        dialog_id: str,
        message: str,
        stream: bool = True,
        message_id: str | None = None,
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

        # 配置 thread_id 用于持久化，同时提高 recursion_limit 以避免复杂 agent 循环超限
        config = {"configurable": {"thread_id": dialog_id}, "recursion_limit": 100}

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

                # # stream_mode=["messages"] 返回元组 (stream_mode, (AIMessageChunk, metadata))
                # # 注意：LangGraph 返回的是嵌套元组结构
                # if isinstance(raw_event, tuple) and len(raw_event) == 2:
                #     stream_mode, inner_data = raw_event

                #     # 处理嵌套元组: (AIMessageChunk, metadata_dict)
                #     if isinstance(inner_data, tuple) and len(inner_data) == 2:
                #         message_chunk, metadata = inner_data
                #         self._update_logger.debug("Unpacked nested tuple: stream_mode={}, chunk_type={}", stream_mode, type(message_chunk).__name__)
                #     else:
                #         # 直接的 AIMessageChunk (非嵌套格式)
                #         message_chunk = inner_data
                #         metadata = {}
                #         self._update_logger.debug("Direct chunk: stream_mode={}, chunk_type={}", stream_mode, type(message_chunk).__name__)

                #     self._update_logger.debug("Got message chunk: mode={}, type={}, content={}", stream_mode, type(message_chunk).__name__, repr(getattr(message_chunk, 'content', ''))[:200])

                #     # 检测新消息开始（通过 message id）
                #     current_msg_id = getattr(message_chunk, 'id', None)
                #     if current_msg_id and current_msg_id != last_message_id:
                #         if last_message_id is not None:
                #             # 新消息开始，重置累积内容
                #             self._update_logger.debug("New message detected, resetting accumulated_content. old_msg={}, new_msg={}", last_message_id, current_msg_id)
                #             accumulated_content = ""
                #         last_message_id = current_msg_id
                # else:
                #     self._update_logger.warning("Unexpected event format: {}", type(raw_event))
                #     continue

                # # 处理 ToolMessage - 记录到 JSONL 文件但不渲染到前端
                # if hasattr(message_chunk, 'type') and message_chunk.type == 'tool':
                #     tool_call_id = getattr(message_chunk, 'tool_call_id', 'unknown')
                #     tool_content = getattr(message_chunk, 'content', '')
                #     tool_name = getattr(message_chunk, 'name', 'unknown')

                #     # 写入工具结果到 JSONL 日志
                #     import json
                #     from datetime import datetime
                #     log_entry = {
                #         "timestamp": datetime.now().isoformat(),
                #         "dialog_id": dialog_id,
                #         "tool_call_id": tool_call_id,
                #         "tool_name": tool_name,
                #         "content": tool_content[:2000] if isinstance(tool_content, str) else str(tool_content)[:2000]  # 限制长度
                #     }
                #     with open("logs/deep/tool_results.jsonl", "a", encoding="utf-8") as f:
                #         json_str = json.dumps(log_entry, ensure_ascii=False)
                #         f.write(json_str + chr(10))

                #     self._update_logger.debug("Tool result logged to JSONL: tool_call_id={}", tool_call_id)
                #     continue

                # # 处理消息块，直接生成 text_delta 事件
                # if hasattr(message_chunk, 'content') and message_chunk.content:
                #     content = message_chunk.content
                #     # 处理 content 是列表的情况 (Anthropic 格式)
                #     if isinstance(content, list):
                #         text_parts = []
                #         for block in content:
                #             if isinstance(block, dict) and block.get('type') == 'text':
                #                 text_parts.append(block.get('text', ''))
                #             elif isinstance(block, str):
                #                 text_parts.append(block)
                #         content = ''.join(text_parts)

                #     if content:
                #         accumulated_content += content
                #         self._log_message_chunk(message_chunk, dialog_id, accumulated_content)
                #         yield AgentEvent(
                #             type="text_delta",
                #             data=content,
                #             metadata={"accumulated_length": len(accumulated_content)}
                #         )

                # 检查工具调用 - 不发送 tool_start 事件到前端
                #                 if hasattr(message_chunk, 'additional_kwargs') and message_chunk.additional_kwargs:
                #                     tool_calls = message_chunk.additional_kwargs.get('tool_calls')
                #                     if tool_calls:
                #                         self._update_logger.info("Tool calls detected: {}", tool_calls)
                #                         yield AgentEvent(type="tool_start", data={"tool_calls": tool_calls})
                # 
                # 检查是否是 ToolMessage (工具执行结果)
                # if hasattr(message_chunk, 'type') and message_chunk.type == 'tool':
                #     tool_call_id = getattr(message_chunk, 'tool_call_id', 'unknown')
                #     tool_content = getattr(message_chunk, 'content', '')
                    # self._update_logger.info("Tool result received: tool_call_id={}", tool_call_id)
                    # yield AgentEvent(type="tool_end", data={
                    #     "tool_call_id": tool_call_id,
                    #     "content": tool_content
                    # })

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