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
    ):
        self.provider = provider or create_provider_from_env()
        self.model = model or (self.provider.default_model if self.provider else "deepseek-chat")
        self.system = system
        self.tools = tools or []
        self.tool_handlers = tool_handlers or {}
        self.max_tokens = max_tokens
        self.max_rounds = max_rounds
        self._hook_delegate: AgentLifecycleHooks | None = None

        # 运行状态
        self._stopped = False

    def _emit_hook(self, hook: HookName, **payload: Any) -> None:
        """发出钩子信号（静默忽略钩子内部错误）。"""
        try:
            logger.info(f"[_emit_hook] hook={hook}, delegate={type(self._hook_delegate).__name__ if self._hook_delegate else None}")
            self.on_hook(hook, **payload)
        except Exception:
            logger.exception(f"Error in hook {hook}, ignoring.")

    def on_hook(self, hook: HookName, **payload: Any) -> None:
        """默认分发到可选 delegate；子类可覆盖。"""
        logger.info(f"[BaseAgentLoop] on_hook called: {hook}, delegate={type(self._hook_delegate).__name__ if self._hook_delegate else None}")
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

    async def arun(self, messages: list[dict]) -> str:
        """异步执行 Agent 循环（推荐用法）

        Args:
            messages: 消息列表，OpenAI 格式

        Returns:
            最终响应内容
        """
        import logging
        logging.getLogger(__name__).debug(f"[BaseAgentLoop] Starting arun with max_tokens={self.max_tokens}, max_rounds={self.max_rounds}, tools={len(self.tools)}")
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

                    # 构建消息列表
                    chat_messages = messages.copy()
                    if self.system:
                        chat_messages = [{"role": "system", "content": self.system}] + chat_messages

                    # 流式处理
                    stream_iterator = provider.chat_stream(
                        messages=chat_messages,
                        tools=self.tools or None,
                        model=self.model,
                        max_tokens=self.max_tokens,
                    )

                    async for chunk in stream_iterator:
                        # 检查是否被请求停止
                        if self._stopped:
                            logger.info("[BaseAgentLoop] Stop requested during streaming, breaking loop")
                            stream_results["done"] = True
                            stream_results["finish_reason"] = "stop"
                            break

                        import logging
                        logging.getLogger(__name__).info(f"[BaseAgentLoop] Chunk received: type={type(chunk).__name__}, is_content={chunk.is_content}, is_reasoning={chunk.is_reasoning}, content={repr(chunk.content)[:50] if chunk.content else 'None'}, reasoning={repr(chunk.reasoning_content)[:50] if chunk.reasoning_content else 'None'}")
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

                    if stream_results["has_error"]:
                        raise RuntimeError(stream_results["errors"])

                    content = stream_results["content"]
                    tool_calls = stream_results["tool_calls"]
                    finish_reason = stream_results["finish_reason"]

                    import logging
                    logging.getLogger(__name__).info(f"[BaseAgentLoop] Stream ended: content_len={len(content)}, tool_calls_count={len(tool_calls)}, finish_reason={finish_reason}")

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
                        logging.getLogger(__name__).info(f"[BaseAgentLoop] No tool calls, returning final_content (len={len(final_content)})")
                        self._emit_hook(HookName.ON_COMPLETE, content=final_content)
                        return final_content

                    if not tool_calls and finish_reason in ("tool_calls", "function_call"):
                        import logging
                        logging.getLogger(__name__).error(f"[BaseAgentLoop] Model requested tool calls but none were parsed from stream chunks")
                        raise RuntimeError("Model requested tool calls but none were parsed from stream chunks")

                    import logging
                    logging.getLogger(__name__).info(f"[BaseAgentLoop] Processing {len(tool_calls)} tool calls")

                    for tc in tool_calls:
                        import logging
                        logging.getLogger(__name__).info(f"[BaseAgentLoop] Emitting ON_TOOL_CALL: name={tc.name}, tool_call_id={tc.id}")
                        self._emit_hook(HookName.ON_TOOL_CALL, name=tc.name, arguments=tc.arguments, tool_call_id=tc.id)

                        handler = self.tool_handlers.get(tc.name)
                        logging.getLogger(__name__).info(f"[BaseAgentLoop] Executing tool: name={tc.name}, handler={handler is not None}")
                        try:
                            result = handler(**tc.arguments) if handler else f"Unknown tool: {tc.name}"
                        except Exception as e:
                            result = f"Error executing {tc.name}: {str(e)}"

                        logging.getLogger(__name__).info(f"[BaseAgentLoop] Tool result: name={tc.name}, result_len={len(str(result))}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": str(result),
                        })
                        logging.getLogger(__name__).info(f"[BaseAgentLoop] Emitting ON_TOOL_RESULT: name={tc.name}, tool_call_id={tc.id}")
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

    def run(self, messages: list[dict]) -> str:
        """同步执行 Agent 循环（向后兼容，内部使用 arun）

        Args:
            messages: 消息列表，OpenAI 格式

        Returns:
            最终响应内容
        """
        try:
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，使用 run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(self.arun(messages), loop)
            return future.result(timeout=120)
        except RuntimeError:
            # 没有事件循环，使用 asyncio.run
            return asyncio.run(self.arun(messages))


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
