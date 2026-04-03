"""Deep Agent Runtime - 基于 deep-agents 框架的 Runtime 实现

使用 deep-agents SDK 的 create_deep_agent() 创建 Agent，
并通过适配器模式包装为 AgentRuntime 接口。
"""

from typing import AsyncIterator, Any, Optional, Callable

from loguru import logger
from pydantic import BaseModel

from core.agent.runtimes.base import AbstractAgentRuntime, ToolCache
from core.models.entities import Dialog
from core.models.config import EngineConfig
from core.types import AgentEvent
from core.models.event_models import UserMessageModel, LangGraphConfigModel
from .services.config_adapter import DeepConfigAdapter, DeepAgentConfig
from .services.tool_adapter import ToolAdapter
from .services.logging_mixin import DeepLoggingMixin
from .services.event_converter import StreamEventConverter, EventConverter
from langchain_anthropic import ChatAnthropic


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
            from deepagents import create_deep_agent
            from deepagents.backends import FilesystemBackend
            from langgraph.checkpoint.memory import MemorySaver
            from langgraph.store.memory import InMemoryStore
        except ImportError as e:
            raise ImportError(
                "deepagents package is required for DeepAgentRuntime. "
                "Install with: pip install deepagents"
            ) from e

        # 转换工具格式
        adapted_tools = self._adapt_tools(self._tools)

        # 配置 checkpointer 和 store
        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.store.memory import InMemoryStore
        self._checkpointer = MemorySaver()
        self._store = InMemoryStore()

        # 配置 backend
        backend = FilesystemBackend(root_dir=".", virtual_mode=True)

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

        # 创建 Deep Agent
        self._agent = create_deep_agent(
            name=self._config.name or self._agent_id,
            model=model,
            tools=adapted_tools,
            system_prompt=self._config.system or self._config.system_prompt,
            backend=backend,
            checkpointer=self._checkpointer,
            store=self._store,
            skills=self._config.skills,
            subagents=self._config.subagents,
            interrupt_on=self._config.interrupt_on,
        )

        logger.info(f"[DeepAgentRuntime] Initialized: {self._agent_id}")

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

    def _adapt_tools(self, tools: dict[str, ToolCache]) -> list:
        """
        将我们的工具格式转换为 LangChain Tool 格式

        Args:
            tools: 我们的工具字典 {name: ToolCache}

        Returns:
            LangChain Tool 列表
        """
        from langchain.tools import tool as langchain_tool

        adapted = []

        for name, tool_info in tools.items():
            handler = tool_info.handler
            description = tool_info.description

            # 创建 LangChain Tool
            @langchain_tool(name=name, description=description)  # type: ignore[call-overload]
            def adapted_tool(**kwargs):
                return handler(**kwargs)

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
        同时记录三种 stream_mode 的日志。

        所有日志写入使用异步队列（enqueue=True），不影响主流程性能。
        """
        if self._agent is None:
            raise RuntimeError("DeepAgentRuntime not initialized. Call initialize() first.")
        

        # 构造消息
        user_msg = UserMessageModel(role="user", content=message)
        if isinstance(user_msg, BaseModel):
            messages = [user_msg.model_dump()]
        else:
            messages = [{"role": "user", "content": message}]

        # 配置 thread_id 用于持久化，同时提高 recursion_limit 以避免复杂 agent 循环超限
        config = {"configurable": {"thread_id": dialog_id}, "recursion_limit": 100}

        # 记录用户消息到三种日志
        self._msg_logger.debug("User message: {}", message[:200])
        self._update_logger.debug("Start conversation: dialog_id={}", dialog_id)
        self._value_logger.debug("Initial state: dialog_id={}, message_count={}", dialog_id, len(messages))

        # 用于累积流式内容
        accumulated_content = ""
        last_message_id = None

        try:
            # 使用 stream_mode="updates" 获取节点级完整状态更新
            self._update_logger.info("Starting astream for dialog={}", dialog_id)
            async for raw_event in self._agent.astream(
                {"messages": messages},
                config,
                stream_mode=["updates"]
            ):
                # stream_mode=["updates"] 返回元组 (stream_mode, data)
                if isinstance(raw_event, tuple) and len(raw_event) == 2:
                    event = raw_event[1]  # 取数据部分
                else:
                    event = raw_event

                self._update_logger.debug("Got raw event: type={}, is_tuple={}, content={}", type(event).__name__, isinstance(event, tuple), repr(event)[:500])
                # 转换并 yield 事件
                agent_event = self._convert_stream_event(event, dialog_id, accumulated_content)

                if agent_event:
                    self._update_logger.info("Yielding agent_event: type={}, data={}", agent_event.type, repr(agent_event.data)[:200])

                    # 将 model_complete 转换为 main.py 能识别的 text_delta + complete
                    if agent_event.type == "model_complete":
                        data = agent_event.data
                        msgs = data.get("messages", []) if isinstance(data, dict) else []
                        ai_content = ""
                        has_tool_calls = False
                        for msg in msgs:
                            if isinstance(msg, dict) and msg.get("type") == "ai":
                                ai_content = self._extract_text_content(msg)
                                # 检查是否包含工具调用
                                raw_content = msg.get("data", {}).get("content", "")
                                if isinstance(raw_content, list):
                                    has_tool_calls = any(
                                        isinstance(block, dict) and block.get("type") == "tool_use"
                                        for block in raw_content
                                    )
                                break

                        if ai_content:
                            dialog = self._dialogs.get(dialog_id)
                            if dialog:
                                dialog.add_ai_message(ai_content, msg_id=message_id)
                            accumulated_content += ai_content
                            self._log_message_chunk(event, dialog_id, accumulated_content)
                            yield AgentEvent(type="text_delta", data=ai_content)

                        # 如果包含工具调用，不发送 complete 事件，等待工具执行完成
                        if not has_tool_calls:
                            yield AgentEvent(type="complete", data=None)
                        continue

                    # 更新累积内容
                    if agent_event.type == "text_delta":
                        accumulated_content += str(agent_event.data)
                        self._log_message_chunk(event, dialog_id, accumulated_content)
                        yield agent_event
                    elif agent_event.type == "tool_start":
                        self._log_tool_start(agent_event, dialog_id)
                        yield agent_event
                    elif agent_event.type == "tool_end":
                        self._log_tool_end(agent_event, dialog_id)
                        yield agent_event
                    else:
                        yield agent_event
                else:
                    # Debug: show what nodes are being filtered and their content
                    if isinstance(event, dict):
                        node_names = list(event.keys())
                        for node_name, state_update in event.items():
                            self._update_logger.debug("Filtered node '{}': {}", node_name, repr(state_update)[:800])
                        self._update_logger.debug("Filtered event from nodes: {}", node_names)

        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            logger.exception(f"[DeepAgentRuntime] Error in send_message: {e}")
            self._msg_logger.error("Error: {}", error_detail)
            self._update_logger.error("Error: {}", str(e))
            self._value_logger.error("Error: {}", str(e))
            yield AgentEvent(type="error", data=str(e))

    def _convert_stream_event(self, event: Any, dialog_id: str, accumulated: str) -> Optional[AgentEvent]:
        """将 Deep Agent 流式事件转换为 AgentEvent"""
        return StreamEventConverter.convert(event, dialog_id, accumulated)

    def _convert_event(self, event: Any) -> Optional[AgentEvent]:
        """将 Deep Agent 事件转换为 AgentEvent"""
        return EventConverter.convert(event)

    async def create_dialog(self, user_input: str, title: Optional[str] = None) -> str:
        """创建新对话"""
        import uuid
        from datetime import datetime
        from core.models.entities import Dialog

        dialog_id = str(uuid.uuid4())

        # 创建对话
        dialog_title = title if title else (user_input[:50] + "..." if len(user_input) > 50 else user_input)
        dialog = Dialog(
            id=dialog_id,
            title=dialog_title,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        dialog.add_human_message(user_input)

        self._dialogs[dialog_id] = dialog

        # 记录创建日志
        self._msg_logger.debug("Dialog created: dialog_id={}, title={}", dialog_id, dialog_title)
        self._update_logger.debug("Dialog created: dialog_id={}", dialog_id)
        self._value_logger.debug("Dialog created: dialog_id={}, initial_message_count=1", dialog_id)

        logger.info(f"[DeepAgentRuntime] Created dialog: {dialog_id}")

        return dialog_id

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

    def get_dialog(self, dialog_id: str) -> Optional[Dialog]:
        """获取对话"""
        return self._dialogs.get(dialog_id)

    def list_dialogs(self) -> list[Dialog]:
        """列出所有对话"""
        return list(self._dialogs.values())

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