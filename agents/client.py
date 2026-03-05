#!/usr/bin/env python3
"""
agents/client.py - 共享的 LLM 客户端

为所有 agent 提供统一的模型客户端配置，使用 LangChain 作为连接层，
并保持与 OpenAI SDK 风格一致的调用接口。
"""

import os
import json
from types import SimpleNamespace
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

# 通用/OpenAI/Azure OpenAI 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL_ID = os.getenv("OPENAI_MODEL_ID", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "")
OPENAI_MODEL_PROVIDER = os.getenv("OPENAI_MODEL_PROVIDER", "deepseek").lower()
OPENAI_SUBSCRIPTION_KEY = os.getenv("OPENAI_SUBSCRIPTION_KEY", "") or os.getenv("APIM_SUBSCRIPTION_KEY", "")

# DeepSeek 兼容配置（向后兼容）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


class _ToolFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, tool_call_id: str, name: str, arguments: str):
        self.id = tool_call_id
        self.function = _ToolFunction(name=name, arguments=arguments)

    def model_dump(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.function.name,
                "arguments": self.function.arguments,
            },
        }


class _AssistantMessage:
    def __init__(self, content: str, tool_calls: list[_ToolCall] | None):
        self.content = content
        self.tool_calls = tool_calls


class _Choice:
    def __init__(self, message: _AssistantMessage, finish_reason: str):
        self.message = message
        self.finish_reason = finish_reason


class _ChatCompletionResponse:
    def __init__(self, choices: list[_Choice]):
        self.choices = choices


class _AnthropicTextBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class _AnthropicToolUseBlock:
    def __init__(self, tool_use_id: str, name: str, input_data: dict[str, Any]):
        self.type = "tool_use"
        self.id = tool_use_id
        self.name = name
        self.input = input_data


class _AnthropicMessagesResponse:
    def __init__(self, content: list[Any], stop_reason: str):
        self.content = content
        self.stop_reason = stop_reason


def _normalize_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def _to_langchain_messages(messages: list[dict[str, Any]]) -> list[Any]:
    lc_messages: list[Any] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content", "")

        if role == "system":
            lc_messages.append(SystemMessage(content=str(content)))
        elif role == "user":
            lc_messages.append(HumanMessage(content=str(content)))
        elif role == "assistant":
            tool_calls = message.get("tool_calls")
            if tool_calls:
                lc_messages.append(
                    AIMessage(
                        content=str(content or ""),
                        additional_kwargs={"tool_calls": tool_calls},
                    )
                )
            else:
                lc_messages.append(AIMessage(content=str(content or "")))
        elif role == "tool":
            lc_messages.append(
                ToolMessage(
                    content=str(content),
                    tool_call_id=message.get("tool_call_id", ""),
                )
            )
    return lc_messages


class _LangChainChatCompletions:
    def __init__(self, llm: ChatOpenAI | AzureChatOpenAI):
        self._llm = llm

    def create(self, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
               max_tokens: int | None = None, **kwargs) -> _ChatCompletionResponse:
        active_llm = self._llm.bind_tools(tools) if tools else self._llm
        invoke_kwargs: dict[str, Any] = {}
        if max_tokens is not None:
            invoke_kwargs["max_tokens"] = max_tokens
        invoke_kwargs.update(kwargs)

        response = active_llm.invoke(_to_langchain_messages(messages), **invoke_kwargs)

        lc_tool_calls = response.tool_calls or []
        tool_calls: list[_ToolCall] = []
        for tool_call in lc_tool_calls:
            args = tool_call.get("args", {})
            arguments = args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)
            tool_calls.append(
                _ToolCall(
                    tool_call_id=tool_call.get("id", ""),
                    name=tool_call.get("name", ""),
                    arguments=arguments,
                )
            )

        assistant_message = _AssistantMessage(
            content=_normalize_content(response.content),
            tool_calls=tool_calls or None,
        )
        finish_reason = "tool_calls" if tool_calls else "stop"
        return _ChatCompletionResponse(choices=[_Choice(message=assistant_message, finish_reason=finish_reason)])


class _AnthropicMessagesCompat:
    """Compatibility layer for existing agents that still call client.messages.create."""

    def __init__(self, outer_client: "_LangChainClient"):
        self._outer_client = outer_client

    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        converted: list[dict[str, Any]] = []
        for tool in tools:
            name = tool.get("name", "")
            description = tool.get("description", "")
            params = tool.get("input_schema", {"type": "object", "properties": {}})
            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": params,
                    },
                }
            )
        return converted

    @staticmethod
    def _convert_messages(system: str | None, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        if system:
            converted.append({"role": "system", "content": system})

        for message in messages:
            role = message.get("role")
            content = message.get("content", "")

            if role == "assistant" and isinstance(content, list):
                text_parts: list[str] = []
                tool_calls: list[dict[str, Any]] = []
                for block in content:
                    block_type = getattr(block, "type", None)
                    if block_type is None and isinstance(block, dict):
                        block_type = block.get("type")
                    if block_type == "text":
                        text = getattr(block, "text", None)
                        if text is None and isinstance(block, dict):
                            text = block.get("text", "")
                        if text:
                            text_parts.append(str(text))
                    elif block_type == "tool_use":
                        tool_id = getattr(block, "id", None)
                        name = getattr(block, "name", None)
                        input_data = getattr(block, "input", None)
                        if isinstance(block, dict):
                            tool_id = tool_id or block.get("id", "")
                            name = name or block.get("name", "")
                            input_data = input_data if input_data is not None else block.get("input", {})
                        tool_calls.append(
                            {
                                "id": tool_id or "",
                                "type": "function",
                                "function": {
                                    "name": name or "",
                                    "arguments": json.dumps(input_data or {}, ensure_ascii=False),
                                },
                            }
                        )
                converted.append(
                    {
                        "role": "assistant",
                        "content": "\n".join(text_parts),
                        "tool_calls": tool_calls or None,
                    }
                )
                continue

            if role == "user" and isinstance(content, list):
                added_tool_results = False
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        converted.append(
                            {
                                "role": "tool",
                                "tool_call_id": block.get("tool_use_id", ""),
                                "content": str(block.get("content", "")),
                            }
                        )
                        added_tool_results = True
                if added_tool_results:
                    continue

            converted.append({"role": role, "content": str(content)})

        return converted

    def create(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
        **kwargs,
    ) -> _AnthropicMessagesResponse:
        openai_tools = self._convert_tools(tools)
        openai_messages = self._convert_messages(system, messages)

        resp = self._outer_client.chat.completions.create(
            model=model,
            messages=openai_messages,
            tools=openai_tools,
            max_tokens=max_tokens,
            **kwargs,
        )

        choice = resp.choices[0]
        assistant_message = choice.message

        content_blocks: list[Any] = []
        if assistant_message.content:
            content_blocks.append(_AnthropicTextBlock(assistant_message.content))

        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                args = tool_call.function.arguments or "{}"
                try:
                    input_data = json.loads(args) if isinstance(args, str) else args
                except json.JSONDecodeError:
                    input_data = {}
                content_blocks.append(
                    _AnthropicToolUseBlock(
                        tool_use_id=tool_call.id,
                        name=tool_call.function.name,
                        input_data=input_data,
                    )
                )

        stop_reason = "tool_use" if choice.finish_reason == "tool_calls" else "end_turn"
        return _AnthropicMessagesResponse(content=content_blocks, stop_reason=stop_reason)


class _LangChainClient:
    def __init__(self, llm: ChatOpenAI | AzureChatOpenAI):
        self.chat = SimpleNamespace(completions=_LangChainChatCompletions(llm))
        self.messages = _AnthropicMessagesCompat(self)


if OPENAI_MODEL_PROVIDER == "azure_openai":
    MODEL = OPENAI_MODEL_ID or "gpt-4o"
    api_key = OPENAI_API_KEY
    base_url = OPENAI_BASE_URL
    default_query = {"api-version": OPENAI_API_VERSION} if OPENAI_API_VERSION else None
    default_headers = {
        "api-key": OPENAI_API_KEY,
    }
    if OPENAI_SUBSCRIPTION_KEY:
        default_headers["Ocp-Apim-Subscription-Key"] = OPENAI_SUBSCRIPTION_KEY
elif OPENAI_MODEL_PROVIDER == "openai":
    MODEL = OPENAI_MODEL_ID or "gpt-4o"
    api_key = OPENAI_API_KEY
    base_url = OPENAI_BASE_URL or None
    default_query = None
    default_headers = None
else:
    MODEL = DEEPSEEK_MODEL
    api_key = DEEPSEEK_API_KEY
    base_url = DEEPSEEK_BASE_URL
    default_query = None
    default_headers = None

# 创建共享客户端（LangChain）
if api_key:
    if OPENAI_MODEL_PROVIDER == "azure_openai":
        azure_endpoint = base_url
        azure_deployment = MODEL

        if base_url and "/openai/deployments/" in base_url:
            endpoint_base, deployment_tail = base_url.split("/openai/deployments/", 1)
            azure_endpoint = endpoint_base
            azure_deployment = deployment_tail.split("/")[0] or MODEL

        llm = AzureChatOpenAI(
            azure_endpoint=azure_endpoint,
            azure_deployment=azure_deployment,
            api_version=OPENAI_API_VERSION or None,
            api_key=api_key,
            default_headers=default_headers,
            temperature=0.1,
        )
    else:
        llm = ChatOpenAI(
            model=MODEL,
            api_key=api_key,
            base_url=base_url if base_url else None,
            default_query=default_query,
            default_headers=default_headers,
            temperature=0.1,
        )

    client = _LangChainClient(llm)
else:
    client = None


def get_client():
    """获取当前配置的模型客户端实例"""
    if client is None:
        raise ValueError("API key not set. Please configure OPENAI_API_KEY or DEEPSEEK_API_KEY.")
    return client


def get_model() -> str:
    """获取当前配置的模型名称"""
    return MODEL
