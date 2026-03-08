"""
BaseAgentLoop - 极简 Agent 循环

使用函数参数传递钩子，无 Mixin、无抽象类、最简实现。
"""

from __future__ import annotations

from asyncio import constants
from email import errors
import json
import asyncio
from pathlib import Path
from typing import Any
from loguru import logger

from .abstract import AgentLifecycleHooks, HookName
from ..providers import LiteLLMProvider, create_provider_from_env


class BaseAgentLoop(AgentLifecycleHooks):
    """极简 Agent 循环基类

    钩子通过函数参数传递，无需继承或 Mixin。

    示例:
        agent = BaseAgentLoop(
            provider=provider,
            system="You are a helpful assistant",
            tools=[...],
        )
        agent.run([{"role": "user", "content": "Hello"}])
    """

    def __init__(
        self,
        provider: LiteLLMProvider | None = None,
        model: str | None = None,
        system: str = "",
        tools: list | None = None,
        tool_handlers: dict | None = None,
        max_tokens: int = 8000,
        max_rounds: int = 25,
<<<<<<< HEAD
=======
        # 钩子函数（可选）
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, dict, Any], None] | None = None,
        on_stream_token: Callable[[str], None] | None = None,
        on_complete: Callable[[str], None] | None = None,
        on_reasoning: Callable[[str], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        on_stop: Callable[[], None] | None = None,

>>>>>>> 4aa0591 (feat: 完善实时对话界面的 Markdown 渲染和工具结果显示)
    ):
        self.provider = provider or create_provider_from_env()
        self.model = model or (self.provider.default_model if self.provider else "deepseek-chat")
        self.system = system
        self.tools = tools or []
        self.tool_handlers = tool_handlers or {}
        self.max_tokens = max_tokens
        self.max_rounds = max_rounds
<<<<<<< HEAD
        self._hook_delegate: AgentLifecycleHooks | None = None
=======

        # 保存钩子
        self._on_tool_call = on_tool_call
        self._on_tool_result = on_tool_result
        self._on_stream_token = on_stream_token
        self._on_complete = on_complete
        self._on_reasoning = on_reasoning
        self._on_error = on_error
        self._on_stop = on_stop
>>>>>>> 4aa0591 (feat: 完善实时对话界面的 Markdown 渲染和工具结果显示)

        # 运行状态
        self._stopped = False

    def _emit_hook(self, hook: HookName, **payload: Any) -> None:
        """发出钩子信号（静默忽略钩子内部错误）。"""
        try:
            self.on_hook(hook, **payload)
        except Exception:
            pass

    def on_hook(self, hook: HookName, **payload: Any) -> None:
        """默认分发到可选 delegate；子类可覆盖。"""
        if self._hook_delegate is not None:
            self._hook_delegate.on_hook(hook, **payload)

    def set_hook_delegate(self, delegate: AgentLifecycleHooks) -> None:
        """Set external hook dispatcher without subclass override."""
        self._hook_delegate = delegate

    def stop(self) -> None:
        """请求停止"""
        self._stopped = True

    def request_stop(self) -> None:
        """请求停止（别名，兼容性）"""
        self.stop()
        self._emit_hook(HookName.ON_STOP)

    def run(self, messages: list[dict]) -> str:
        """执行 Agent 循环

        Args:
            messages: 消息列表，OpenAI 格式

        Returns:
            最终响应内容
        """
        import logging
        logging.getLogger(__name__).debug(f"[BaseAgentLoop] Starting run with max_tokens={self.max_tokens}, max_rounds={self.max_rounds}, tools={len(self.tools)}")
        self._emit_hook(HookName.ON_BEFORE_RUN, messages=messages)
        if self.provider is None:
            raise RuntimeError("No provider available. Please configure provider environment variables.")
        provider = self.provider
        rounds = 0
        final_content = ""

        try:
            while not self._stopped and rounds < self.max_rounds:
                rounds += 1

                try:
                    # 使用列表存储流式结果，避免在闭包中修改外部变量的问题
                    stream_results = {
                        "content": "",
                        "tool_calls": [],
                        "thinking": "",
                        "errors": "",
                        "final": "",
                        "done": False,
                        "finish_reason": None,
                        "has_error": False,
                        "usage": None,
                    }

                    async def _chat():
                        # 构建消息列表
                        chat_messages = messages.copy()
                        if self.system:
                            chat_messages = [{"role": "system", "content": self.system}] + chat_messages

                        async for chunk in provider.chat_stream(
                            messages=chat_messages,
                            tools=self.tools or None,
                            model=self.model,
                            max_tokens=self.max_tokens,
                        ):
                            self._emit_hook(HookName.ON_STREAM_TOKEN, chunk=chunk)
                            if chunk.is_content:
                                stream_results["content"] += chunk.content
                            elif chunk.is_tool_call:
                                stream_results["tool_calls"].append(chunk.tool_call)
                            elif chunk.is_done:
                                stream_results["final"] += stream_results["content"]
                                stream_results["done"] = True
                                stream_results["finish_reason"] = chunk.finish_reason
                                logger.debug(f"[BaseAgentLoop] Chunk is_done, finish_reason={chunk.finish_reason}, content_len={len(stream_results['content'])}")
                            elif chunk.is_error:
                                stream_results["errors"] += chunk.error
                                stream_results["has_error"] = True
                            elif chunk.is_reasoning:
                                stream_results["thinking"] += chunk.reasoning_content
                            elif chunk.usage:
                                stream_results["usage"] = chunk.usage

                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.run_coroutine_threadsafe(_chat(), loop).result(timeout=120)
                    except RuntimeError:
                        asyncio.run(_chat())

<<<<<<< HEAD
                    if stream_results["has_error"]:
                        raise RuntimeError(stream_results["errors"])
=======
                    # 广播工具执行结果
                    self._emit("tool_result", tc.name, tc.arguments, result, tc.id)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(result),
                    })
>>>>>>> 4aa0591 (feat: 完善实时对话界面的 Markdown 渲染和工具结果显示)

                    content = stream_results["content"]
                    tool_calls = stream_results["tool_calls"]
                    finish_reason = stream_results["finish_reason"]

                    assistant_msg: dict = {"role": "assistant", "content": content, "reasoning_content": stream_results["thinking"]}
                    if tool_calls:
                        assistant_msg["tool_calls"] = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else tc.arguments,
                                },
                            }
                            for tc in tool_calls
                        ]

                    messages.append(assistant_msg)
                    final_content = content

                    if not tool_calls and finish_reason not in ("tool_calls", "function_call"):
                        import logging
                        logging.getLogger(__name__).debug(f"[BaseAgentLoop] No tool calls, returning final_content (len={len(final_content)})")
                        self._emit_hook(HookName.ON_COMPLETE, content=final_content)
                        return final_content

                    if not tool_calls and finish_reason in ("tool_calls", "function_call"):
                        raise RuntimeError("Model requested tool calls but none were parsed from stream chunks")

                    for tc in tool_calls:
                        self._emit_hook(HookName.ON_TOOL_CALL, name=tc.name, arguments=tc.arguments)

                        handler = self.tool_handlers.get(tc.name)
                        try:
                            result = handler(**tc.arguments) if handler else f"Unknown tool: {tc.name}"
                        except Exception as e:
                            result = f"Error executing {tc.name}: {str(e)}"

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": str(result),
                        })
                        self._emit_hook(
                            HookName.ON_TOOL_RESULT,
                            name=tc.name,
                            result=str(result),
                            tool_call_id=tc.id,
                            assistant_message=assistant_msg,
                        )

                except Exception as e:
                    self._emit_hook(HookName.ON_ERROR, error=e)
                    raise

            return final_content
        finally:
            self._emit_hook(HookName.ON_AFTER_RUN, messages=messages, rounds=rounds)


def run_agent(
    messages: list[dict],
    system: str = "",
    tools: list | None = None,
    tool_handlers: dict | None = None,
) -> str:
    """函数式接口 - 一行代码运行 Agent

    示例:
        result = run_agent(
            messages=[{"role": "user", "content": "Hello"}],
            system="You are helpful",
        )
    """
    agent = BaseAgentLoop(
        system=system,
        tools=tools,
        tool_handlers=tool_handlers,
    )
    return agent.run(messages)


__all__ = ["BaseAgentLoop", "run_agent"]
