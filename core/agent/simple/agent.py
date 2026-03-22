"""
SimpleAgent - 当前简单实现，不依赖任何框架

基于原始的 BaseAgentLoop 重构，实现 AgentInterface 接口。
"""

import asyncio
import json
from typing import AsyncIterator, Callable, Optional, Any, List
from loguru import logger

from ..interface import AgentInterface, AgentLifecycleHooks
from ...types import AgentStatus, AgentMessage, AgentEvent, ToolResult, HookName
from ...models.types import (
    MessageDict, ToolCallDict, ToolCallFunctionDict,
    ConversationMessageDict, ConversationStateDict,
)
from ...providers import LiteLLMProvider, create_provider_from_env
from ...tools import ToolRegistry


class SimpleAgent(AgentInterface, AgentLifecycleHooks):
    """
    简单 Agent 实现

    特点:
    - 无外部依赖（除了 litellm）
    - 直接调用 LLM provider
    - 手动处理工具调用循环
    - 适合理解原理和快速原型
    """

    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._status = AgentStatus.IDLE
        self._provider: Optional[LiteLLMProvider] = None
        self._tools = ToolRegistry()
        self._stop_event = asyncio.Event()
        self._messages: list[AgentMessage] = []
        self._config: dict = {}
        self._system_prompt: str = ""
        self._hook_delegate: Optional[AgentLifecycleHooks] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def status(self) -> AgentStatus:
        return self._status

    async def initialize(self, config: dict) -> None:
        """初始化 - 配置 provider 和工具"""
        self._config = config
        self._system_prompt = config.get("system", "")

        # 初始化 provider
        if config.get("provider"):
            self._provider = config["provider"]
        else:
            self._provider = create_provider_from_env() or LiteLLMProvider(
                model=config.get("model", "deepseek/deepseek-chat"),
                api_key=config.get("api_key"),
                base_url=config.get("base_url"),
            )

        # 注册工具
        for tool_config in config.get("tools", []):
            self._tools.register(
                name=tool_config["name"],
                handler=tool_config["handler"],
                description=tool_config["description"],
                schema=tool_config.get("schema") or tool_config.get("parameters"),
            )

        assert self._provider is not None
        logger.info(f"[SimpleAgent] Initialized with model: {self._provider.default_model}")

    async def run(
        self,
        user_input: str,
        context: Optional[list[AgentMessage]] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]:
        """
        运行 Agent - 简单循环实现

        流程: user input → LLM → (tool call → execute → repeat) → final answer
        """
        self._status = AgentStatus.RUNNING
        self._stop_event.clear()

        # 构建消息列表
        messages = list(context) if context else []
        messages.append(AgentMessage(role="user", content=user_input))
        self._messages = messages

        system = system_prompt or self._system_prompt

        try:
            max_iterations = self._config.get("max_iterations", 10)
            max_rounds = self._config.get("max_rounds", 25)

            for iteration in range(min(max_iterations, max_rounds)):
                if self._stop_event.is_set():
                    yield AgentEvent(type="stopped", data="User stopped")
                    break

                # 发出钩子
                self._emit_hook(HookName.ON_BEFORE_RUN, messages=self._convert_messages(messages))

                # 1. 调用 LLM (流式)
                self._status = AgentStatus.THINKING
                logger.info(f"[SimpleAgent] Iteration {iteration + 1}, calling LLM...")

                chat_messages = self._convert_messages(messages)

                # 2. 处理流式响应
                content = ""
                thinking = ""
                tool_calls = []

                if self._provider is None:
                    raise RuntimeError("[SimpleAgent] Provider not initialized. Call initialize() first.")
                async for chunk in self._provider.chat_stream(
                    messages=chat_messages,
                    tools=self._tools.get_schemas() if len(self._tools) > 0 else None,
                    max_tokens=self._config.get("max_tokens", 8000),
                ):
                    if self._stop_event.is_set():
                        break

                    # 发出流式 token 钩子
                    self._emit_hook(HookName.ON_STREAM_TOKEN, chunk=chunk)

                    if chunk.is_content:
                        content += chunk.content
                        yield AgentEvent(
                            type="text_delta",
                            data=chunk.content,
                            metadata={"iteration": iteration},
                        )
                    elif chunk.is_reasoning:
                        thinking += chunk.reasoning_content
                        yield AgentEvent(
                            type="reasoning_delta",
                            data=chunk.reasoning_content,
                            metadata={"iteration": iteration},
                        )
                    elif chunk.is_tool_call:
                        tool_calls.append(chunk.tool_call)
                    elif chunk.is_done:
                        break
                    elif chunk.is_error:
                        raise RuntimeError(chunk.error)

                # 3. 构建 assistant 消息
                assistant_msg = AgentMessage(
                    role="assistant",
                    content=content,
                    metadata={"thinking": thinking} if thinking else None,
                )

                # 如果有工具调用，添加到消息
                if tool_calls:
                    assistant_msg.tool_calls = [
                        ToolCallDict(
                            id=tc["id"],
                            type="function",
                            function=ToolCallFunctionDict(
                                name=tc["name"],
                                arguments=json.dumps(tc["arguments"]),
                            ),
                        )
                        for tc in tool_calls
                    ]

                messages.append(assistant_msg)

                # 4. 如果没有工具调用，直接返回
                if not tool_calls:
                    logger.info(f"[SimpleAgent] No tool calls, returning final answer")
                    self._emit_hook(HookName.ON_COMPLETE, content=content)
                    yield AgentEvent(
                        type="complete",
                        data=content,
                        metadata={"messages": messages, "thinking": thinking},
                    )
                    break

                # 5. 执行工具调用
                logger.info(f"[SimpleAgent] Executing {len(tool_calls)} tool calls")

                for tc in tool_calls:
                    if self._stop_event.is_set():
                        break

                    self._status = AgentStatus.TOOL_CALLING
                    tool_name = tc["name"]
                    tool_args = tc["arguments"]
                    tool_call_id = tc["id"]

                    # 通知工具开始
                    self._emit_hook(HookName.ON_TOOL_CALL, name=tool_name, arguments=tool_args, tool_call_id=tool_call_id)
                    yield AgentEvent(
                        type="tool_start",
                        data={"name": tool_name, "args": tool_args},
                        metadata={"tool_call_id": tool_call_id},
                    )

                    # 执行工具
                    try:
                        result = await self._tools.execute(tool_name, tool_args)
                        tool_result = ToolResult(
                            tool_name=tool_name,
                            tool_call_id=tool_call_id,
                            output=str(result),
                        )
                    except Exception as e:
                        tool_result = ToolResult(
                            tool_name=tool_name,
                            tool_call_id=tool_call_id,
                            output="",
                            error=str(e),
                        )

                    # 添加工具结果到消息
                    messages.append(AgentMessage(
                        role="tool",
                        content=tool_result.output or tool_result.error or "",
                        tool_call_id=tool_call_id,
                    ))

                    # 通知工具完成
                    self._emit_hook(
                        HookName.ON_TOOL_RESULT,
                        name=tool_name,
                        result=tool_result.output or tool_result.error,
                        tool_call_id=tool_call_id,
                    )
                    yield AgentEvent(
                        type="tool_end",
                        data=tool_result,
                        metadata={"tool_call_id": tool_call_id},
                    )

                # 继续循环，让 LLM 基于工具结果继续思考

            else:
                # 达到最大迭代次数
                logger.warning(f"[SimpleAgent] Max iterations reached")
                yield AgentEvent(
                    type="error",
                    data="Max iterations reached",
                    metadata={"max_iterations": max_iterations},
                )

        except Exception as e:
            self._status = AgentStatus.ERROR
            logger.exception(f"[SimpleAgent] Error during run")
            self._emit_hook(HookName.ON_ERROR, error=e)
            yield AgentEvent(type="error", data=str(e))

        finally:
            self._emit_hook(HookName.ON_AFTER_RUN, messages=self._convert_messages(messages), rounds=len(messages))
            if self._status != AgentStatus.ERROR:
                self._status = AgentStatus.IDLE

    async def stop(self) -> None:
        """停止运行"""
        self._stop_event.set()
        self._status = AgentStatus.STOPPED
        self._emit_hook(HookName.ON_STOP)
        logger.info(f"[SimpleAgent] Stopped")

    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        schema: Optional[dict] = None,
    ) -> None:
        """注册工具"""
        self._tools.register(name, handler, description, schema)
        logger.debug(f"[SimpleAgent] Registered tool: {name}")

    def unregister_tool(self, name: str) -> None:
        """注销工具"""
        self._tools.unregister(name)
        logger.debug(f"[SimpleAgent] Unregistered tool: {name}")

    async def get_conversation_state(self) -> ConversationStateDict:
        """获取对话状态"""
        return ConversationStateDict(
            agent_id=self._agent_id,
            messages=[
                ConversationMessageDict(
                    role=m.role,
                    content=m.content,
                    tool_calls=m.tool_calls,
                    tool_call_id=m.tool_call_id,
                    metadata=m.metadata,
                )
                for m in self._messages
            ],
            config=self._config,
        )

    async def restore_conversation_state(self, state: ConversationStateDict) -> None:
        """恢复对话状态"""
        self._messages = [
            AgentMessage(**m) for m in state.get("messages", [])
        ]
        self._config = state.get("config", {})

    def set_hook_delegate(self, delegate: AgentLifecycleHooks) -> None:
        """设置钩子委托"""
        self._hook_delegate = delegate

    def on_hook(self, hook: HookName, **payload: Any) -> None:
        """钩子回调分发"""
        if self._hook_delegate is not None:
            try:
                self._hook_delegate.on_hook(hook, **payload)
            except Exception:
                logger.exception(f"Error in hook {hook}, ignoring.")

    def _emit_hook(self, hook: HookName, **payload: Any) -> None:
        """发出钩子"""
        try:
            self.on_hook(hook, **payload)
        except Exception:
            logger.exception(f"Error in hook {hook}, ignoring.")

    def _convert_messages(self, messages: list[AgentMessage]) -> List[MessageDict]:
        """转换为 provider 需要的格式"""
        result: List[MessageDict] = []
        for m in messages:
            msg = MessageDict(role=m.role, content=m.content or "")
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            result.append(msg)
        return result
