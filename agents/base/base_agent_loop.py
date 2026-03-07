from __future__ import annotations

import re
from typing import Any, Callable
from loguru import logger


class BaseAgentLoop:
    """通用 Agent 循环基类。

    目标：把“模型返回 tool_use -> 执行工具 -> 回传 tool_result”的通用流程抽出来，
    供不同脚本复用，减少重复代码。
    """

    def __init__(
        self,
        client: Any,
        model: str,
        system: str,
        tools: list[Any],
        tool_handlers: dict[str, Callable[..., Any]] | None = None,
        max_tokens: int = 8000,
        max_rounds: int | None = 25,
        on_before_round: Callable[[list[dict[str, Any]]], None] | None = None,
        on_tool_call: Callable[[str, dict[str, Any], list[dict[str, Any]]], None] | None = None,
        on_tool_result: Callable[[Any, str, list[dict[str, Any]], list[dict[str, Any]]], None] | None = None,
        on_stream_token: Callable[[str, Any, list[dict[str, Any]], Any], None] | None = None,
        on_stream_text: Callable[[str, Any, list[dict[str, Any]], Any], None] | None = None,
        on_round_end: Callable[[list[dict[str, Any]], list[dict[str, Any]], Any], None] | None = None,
        on_after_round: Callable[[list[dict[str, Any]], Any], None] | None = None,
        on_stop: Callable[[list[dict[str, Any]], Any], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ):
        self.client = client
        self.model = model
        self.system = system
        self.tools, self.tool_handlers = self._normalize_tools(tools, tool_handlers)
        self.max_tokens = max_tokens
        self.max_rounds = max_rounds
        self.on_before_round = on_before_round
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self.on_stream_token = on_stream_token
        self.on_stream_text = on_stream_text
        self.on_round_end = on_round_end
        self.on_after_round = on_after_round
        self.on_stop = on_stop
        self.should_stop = should_stop

    @classmethod
    def from_namespace(
        cls,
        *,
        client: Any,
        model: str,
        system: str,
        namespace: dict[str, Any],
        max_tokens: int = 8000,
        max_rounds: int | None = 25,
        on_before_round: Callable[[list[dict[str, Any]]], None] | None = None,
        on_tool_call: Callable[[str, dict[str, Any], list[dict[str, Any]]], None] | None = None,
        on_tool_result: Callable[[Any, str, list[dict[str, Any]], list[dict[str, Any]]], None] | None = None,
        on_stream_token: Callable[[str, Any, list[dict[str, Any]], Any], None] | None = None,
        on_stream_text: Callable[[str, Any, list[dict[str, Any]], Any], None] | None = None,
        on_round_end: Callable[[list[dict[str, Any]], list[dict[str, Any]], Any], None] | None = None,
        on_after_round: Callable[[list[dict[str, Any]], Any], None] | None = None,
        on_stop: Callable[[list[dict[str, Any]], Any], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> "BaseAgentLoop":
        """从命名空间中自动扫描 @tool 函数并创建循环实例。"""
        from .toolkit import scan_tools

        tools = scan_tools(namespace)
        return cls(
            client=client,
            model=model,
            system=system,
            tools=tools,
            tool_handlers=None,
            max_tokens=max_tokens,
            max_rounds=max_rounds,
            on_before_round=on_before_round,
            on_tool_result=on_tool_result,
            on_stream_token=on_stream_token,
            on_stream_text=on_stream_text,
            on_round_end=on_round_end,
            on_after_round=on_after_round,
            on_stop=on_stop,
            should_stop=should_stop,
        )

    @staticmethod
    def _iter_tokens(text: str) -> list[str]:
        """将文本拆分为 token 片段（保留空白），用于流式输出。"""
        if not text:
            return []
        return re.findall(r"\S+|\s+", text)

    def _emit_stream_tokens(self, text: str, block: Any, messages: list[dict[str, Any]], response: Any) -> None:
        """触发 token 流式钩子。"""
        logger.info(f"[BaseAgentLoop] _emit_stream_tokens called, text length={len(text)}, on_stream_token={self.on_stream_token is not None}")
        if not self.on_stream_token:
            logger.info("[BaseAgentLoop] on_stream_token is None, skipping")
            return
        tokens = self._iter_tokens(text)
        logger.info(f"[BaseAgentLoop] Emitting {len(tokens)} tokens")
        for token in tokens:
            try:
                self.on_stream_token(token, block, messages, response)
            except Exception as e:
                # token 流式回调仅用于展示，不应影响主流程。
                logger.info(f"[BaseAgentLoop] on_stream_token error: {e}")
                import traceback
                traceback.print_exc()
                pass

    def _emit_stream_text(self, response: Any, messages: list[dict[str, Any]]) -> None:
        """触发流式文本钩子：按响应中的文本块顺序回调。"""
        logger.info(f"[BaseAgentLoop] _emit_stream_text called, on_stream_text={self.on_stream_text is not None}, on_stream_token={self.on_stream_token is not None}")
        if not self.on_stream_text and not self.on_stream_token:
            logger.info("[BaseAgentLoop] Both callbacks are None, skipping")
            return

        content = getattr(response, "content", None)
        logger.info(f"[BaseAgentLoop] response.content type={type(content)}")
        if isinstance(content, str):
            if content:
                logger.info(f"[BaseAgentLoop] Emitting string content, length={len(content)}")
                self._emit_stream_tokens(content, None, messages, response)
                try:
                    if self.on_stream_text:
                        self.on_stream_text(content, None, messages, response)
                except Exception as e:
                    logger.info(f"[BaseAgentLoop] on_stream_text error: {e}")
                    import traceback
                    traceback.print_exc()
                    pass
            else:
                logger.info("[BaseAgentLoop] String content is empty")
            return

        if not isinstance(content, list):
            return

        for block in content:
            text = None

            block_type = getattr(block, "type", None)
            if block_type == "text":
                text = getattr(block, "text", None)

            if text is None and isinstance(block, dict):
                if block.get("type") == "text":
                    text = block.get("text")

            if not text:
                continue

            self._emit_stream_tokens(str(text), block, messages, response)

            try:
                if self.on_stream_text:
                    self.on_stream_text(str(text), block, messages, response)
            except Exception:
                # 流式回调仅用于展示，不应影响主流程。
                pass

    @staticmethod
    def _normalize_tools(
        tools: list[Any],
        tool_handlers: dict[str, Callable[..., Any]] | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Callable[..., Any]]]:
        """规范化工具定义。

        支持两种输入：
        1) 传统模式：`tools` + `tool_handlers`
        2) 合并模式：`tools` 中每项可直接包含 `handler`
        3) 函数模式：`tools` 列表中放 `@tool` 标记函数
        """
        handlers: dict[str, Callable[..., Any]] = dict(tool_handlers or {})
        normalized_tools: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        for item in tools:
            if callable(item):
                spec = getattr(item, "__tool_spec__", None)
                if not spec:
                    raise ValueError(
                        f"Callable tool '{getattr(item, '__name__', '<anonymous>')}' is missing @tool decorator"
                    )

                name = spec.get("name")
                if not name:
                    raise ValueError("Callable tool has empty name in __tool_spec__")
                if name in seen_names:
                    raise ValueError(f"Duplicate tool name: '{name}'")
                seen_names.add(name)

                handlers[name] = item
                normalized_tools.append(
                    {
                        "name": name,
                        "description": spec.get("description", f"Tool: {name}"),
                        "input_schema": spec.get("input_schema", {"type": "object", "properties": {}, "required": []}),
                    }
                )
                continue

            if not isinstance(item, dict):
                raise ValueError(f"Unsupported tool entry type: {type(item).__name__}")

            tool_item = dict(item)
            name = tool_item.get("name")
            if not name:
                raise ValueError("Each tool must include a non-empty 'name'")
            if name in seen_names:
                raise ValueError(f"Duplicate tool name: '{name}'")
            seen_names.add(name)

            merged_handler = tool_item.pop("handler", None)
            if merged_handler is not None:
                if not callable(merged_handler):
                    raise ValueError(f"Tool '{name}' has non-callable handler")
                handlers[name] = merged_handler

            normalized_tools.append(tool_item)

        return normalized_tools, handlers

    def run(self, messages: list[dict[str, Any]]) -> None:
        """执行标准循环，直到模型不再请求工具。"""
        import threading
        rounds = 0
        while True:
            # 检查是否应该停止
            if self.should_stop:
                should_stop_result = self.should_stop()
                logger.info(f"[BaseAgentLoop] should_stop check: result={should_stop_result}, thread={threading.current_thread().name}")
                if should_stop_result:
                    logger.info("[BaseAgentLoop] Stop requested, breaking loop")
                    print("[BaseAgentLoop] Stop requested - exiting agent loop")  # Console output for visibility
                    if self.on_stop:
                        self.on_stop(messages, None)
                    return

            # 达到最大轮数时直接停止，避免触发一轮无响应的 before_round 事件。
            if self.max_rounds is not None and rounds >= self.max_rounds:
                logger.info(f"[BaseAgentLoop] Reached max_rounds={self.max_rounds}, stopping")
                if self.on_stop:
                    self.on_stop(messages, None)
                return

            if self.on_before_round:
                self.on_before_round(messages)

            response = self.client.messages.create(
                model=self.model,
                system=self.system,
                messages=messages,
                tools=self.tools,
                max_tokens=self.max_tokens,
            )
            rounds += 1

            self._emit_stream_text(response, messages)

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                if self.on_stop:
                    self.on_stop(messages, response)
                return

            results: list[dict[str, Any]] = []
            for block in response.content:
                if getattr(block, "type", None) != "tool_use":
                    continue

                # 检查是否应该停止（工具调用前）
                if self.should_stop:
                    should_stop_result = self.should_stop()
                    logger.info(f"[BaseAgentLoop] should_stop check during tool call: result={should_stop_result}")
                    if should_stop_result:
                        logger.info("[BaseAgentLoop] Stop requested during tool calls, breaking loop")
                        print("[BaseAgentLoop] Stop requested during tool calls - exiting agent loop")
                        if self.on_stop:
                            self.on_stop(messages, response)
                        return

                # 触发工具调用开始回调
                if self.on_tool_call:
                    try:
                        self.on_tool_call(block.name, block.input, messages)
                    except Exception as e:
                        logger.info(f"[BaseAgentLoop] on_tool_call error: {e}")
                handler = self.tool_handlers.get(block.name)
                try:
                    output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                except Exception as e:
                    output = f"Error: {e}"

                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(output),
                    }
                )

                if self.on_tool_result:
                    self.on_tool_result(block, str(output), results, messages)

            if self.on_round_end:
                self.on_round_end(results, messages, response)

            messages.append({"role": "user", "content": results})

            if self.on_after_round:
                self.on_after_round(messages, response)


def run_base_agent_loop(
    client: Any,
    model: str,
    system: str,
    tools: list[Any],
    tool_handlers: dict[str, Callable[..., Any]] | None,
    messages: list[dict[str, Any]],
    max_tokens: int = 8000,
    max_rounds: int | None = None,
    on_before_round: Callable[[list[dict[str, Any]]], None] | None = None,
    on_tool_call: Callable[[str, dict[str, Any], list[dict[str, Any]]], None] | None = None,
    on_tool_result: Callable[[Any, str, list[dict[str, Any]], list[dict[str, Any]]], None] | None = None,
    on_stream_token: Callable[[str, Any, list[dict[str, Any]], Any], None] | None = None,
    on_stream_text: Callable[[str, Any, list[dict[str, Any]], Any], None] | None = None,
    on_round_end: Callable[[list[dict[str, Any]], list[dict[str, Any]], Any], None] | None = None,
    on_after_round: Callable[[list[dict[str, Any]], Any], None] | None = None,
    on_stop: Callable[[list[dict[str, Any]], Any], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> None:
    """函数式入口：快速执行一次基础 Agent 循环。"""
    loop = BaseAgentLoop(
        client=client,
        model=model,
        system=system,
        tools=tools,
        tool_handlers=tool_handlers,
        max_tokens=max_tokens,
        max_rounds=max_rounds,
        on_before_round=on_before_round,
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
        on_stream_token=on_stream_token,
        on_stream_text=on_stream_text,
        on_round_end=on_round_end,
        on_after_round=on_after_round,
        on_stop=on_stop,
        should_stop=should_stop,
    )
    loop.run(messages)
