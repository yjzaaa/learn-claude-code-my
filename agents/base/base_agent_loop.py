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
from typing import Any, Callable
from loguru import logger

from ..providers import LiteLLMProvider, create_provider_from_env


class BaseAgentLoop:
    """极简 Agent 循环基类

    钩子通过函数参数传递，无需继承或 Mixin。

    示例:
        agent = BaseAgentLoop(
            provider=provider,
            system="You are a helpful assistant",
            tools=[...],
            on_tool_call=lambda name, inp: print(f"Tool: {name}"),
            on_stream_token=lambda t: print(t, end=""),
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
        # 钩子函数（可选）
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_stream_token: Callable[[str], None] | None = None,
        on_complete: Callable[[str], None] | None = None,
        on_reasoning: Callable[[str], None] | None = None,  
        on_error: Callable[[Exception], None] | None = None,
        on_stop: Callable[[], None] | None = None,

    ):
        self.provider = provider or create_provider_from_env()
        self.model = model or (self.provider.default_model if self.provider else "deepseek-chat")
        self.system = system
        self.tools = tools or []
        self.tool_handlers = tool_handlers or {}
        self.max_tokens = max_tokens
        self.max_rounds = max_rounds

        # 保存钩子
        self._on_tool_call = on_tool_call
        self._on_stream_token = on_stream_token
        self._on_complete = on_complete
        self._on_reasoning = on_reasoning
        self._on_error = on_error
        self._on_stop = on_stop

        # 运行状态
        self._stopped = False

    def _emit(self, name: str, *args) -> None:
        """调用钩子（静默忽略错误）"""
        hook = getattr(self, f"_on_{name}", None)
        if hook:
            try:
                hook(*args)
            except Exception:
                pass

    def stop(self) -> None:
        """请求停止"""
        self._stopped = True

    def request_stop(self) -> None:
        """请求停止（别名，兼容性）"""
        self.stop()
        self._emit("stop")

    def run(self, messages: list[dict]) -> str:
        """执行 Agent 循环

        Args:
            messages: 消息列表，OpenAI 格式

        Returns:
            最终响应内容
        """
        import logging
        logging.getLogger(__name__).debug(f"[BaseAgentLoop] Starting run with max_tokens={self.max_tokens}, max_rounds={self.max_rounds}, tools={len(self.tools)}")
        rounds = 0
        final_content = ""

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
                    "has_error": False,
                    "usage": None,
                }

                async def _chat():
                    # 构建消息列表
                    chat_messages = messages.copy()
                    if self.system:
                        chat_messages = [{"role": "system", "content": self.system}] + chat_messages

                    async for chunk in self.provider.chat_stream(
                        messages=chat_messages,
                        tools=self.tools or None,
                        model=self.model,
                        max_tokens=self.max_tokens,
                    ):
                        self._emit("stream_token", chunk)
                        # 内容块
                        if chunk.is_content:
                            stream_results["content"] += chunk.content
                            # if self._on_stream_token:
                            #     self._emit("stream_token", "is_content", chunk.content)
                        
                        # 工具调用
                        elif chunk.is_tool_call:
                            stream_results["tool_calls"].append(chunk.tool_call)
                            # if self._on_tool_call:
                                # self._emit("stream_token", "is_tool_call", chunk.tool_call)
                        
                        # 完成
                        elif chunk.is_done:
                            stream_results["final"] += stream_results["content"]
                            stream_results["done"] = True
                            logger.debug(f"[BaseAgentLoop] Chunk is_done, finish_reason={chunk.finish_reason}, content_len={len(stream_results['content'])}")
                            # if self._on_complete:
                            #     self._emit("stream_token", "is_done", chunk.finish_reason)
                        
                        # 错误
                        elif chunk.is_error:
                            stream_results["errors"] += chunk.error
                            stream_results["has_error"] = True
                            # if self._on_error:
                            #     self._emit("stream_token", "is_error", chunk.error)
                        
                        # 推理内容
                        elif chunk.is_reasoning:
                            stream_results["thinking"] += chunk.reasoning_content
                            # if self._on_reasoning:
                            #     self._emit("stream_token", "is_reasoning", chunk.reasoning_content)
                        #token用量
                        elif chunk.usage:
                            stream_results["usage"] = chunk.usage
                            # self._emit("stream_token", "usage", chunk.usage)

                # 运行异步
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.run_coroutine_threadsafe(_chat(), loop).result(timeout=120)
                except RuntimeError:
                    asyncio.run(_chat())

                # 检查错误
                if stream_results["has_error"]:
                    raise RuntimeError(stream_results["errors"])

                content = stream_results["content"]
                tool_calls = stream_results["tool_calls"]

                # 构建 assistant 消息
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

                # 检查是否完成
                if not tool_calls:
                    import logging
                    logging.getLogger(__name__).debug(f"[BaseAgentLoop] No tool calls, returning final_content (len={len(final_content)})")
                    self._emit("complete", final_content)
                    return final_content

                # 执行工具调用
                for tc in tool_calls:
                    self._emit("tool_call", tc.name, tc.arguments)

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

            except Exception as e:
                self._emit("error", str(e))
                raise

        return final_content


def run_agent(
    messages: list[dict],
    system: str = "",
    tools: list | None = None,
    tool_handlers: dict | None = None,
    on_tool_call: Callable | None = None,
    on_stream_token: Callable | None = None,
) -> str:
    """函数式接口 - 一行代码运行 Agent

    示例:
        result = run_agent(
            messages=[{"role": "user", "content": "Hello"}],
            system="You are helpful",
            on_stream_token=lambda t: print(t, end=""),
        )
    """
    agent = BaseAgentLoop(
        system=system,
        tools=tools,
        tool_handlers=tool_handlers,
        on_tool_call=on_tool_call,
        on_stream_token=on_stream_token,
    )
    return agent.run(messages)


__all__ = ["BaseAgentLoop", "run_agent"]
