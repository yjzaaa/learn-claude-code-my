"""
LiteLLM Provider - 基于 LiteLLM 的 Provider 实现

支持多种 LLM 后端（OpenAI, Anthropic, DeepSeek 等）
"""

import os
from typing import AsyncIterator, List, Optional

from httpx import stream
from backend.infrastructure.protocols.provider import BaseProvider
from backend.domain.models.shared import StreamChunk
from backend.domain.models.shared.types import MessageDict, StreamToolCallDict

# 在模块级别检查 litellm 是否可用
try:
    import litellm
    _LITELLM_AVAILABLE = True
except ImportError:
    _LITELLM_AVAILABLE = False
    litellm = None


class LiteLLMProvider(BaseProvider):
    """
    基于 LiteLLM 的 Provider 实现
    
    支持:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - DeepSeek
    - 其他 LiteLLM 支持的模型
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "deepseek/deepseek-chat",
    ):
        if not _LITELLM_AVAILABLE:
            raise ImportError(
                "litellm is required. Install with: pip install litellm"
            )

        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._default_model = default_model
        self._litellm = litellm
    
    @property
    def default_model(self) -> str:
        return self._default_model
    
    async def chat_stream(
        self,
        messages: List[MessageDict],
        model: Optional[str] = None,
        tools: Optional[list] = None,
        max_tokens: int = 8000,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """
        流式聊天实现
        
        使用 LiteLLM 的 acompletion 函数
        """
        import json
        
        model_name = model or self._model or self._default_model
        
        # 构建请求参数
        kwargs = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        
        if tools:
            kwargs["tools"] = tools
        
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["base_url"] = self._base_url
        
        # 调用 LiteLLM
        response = await self._litellm.acompletion(**kwargs)
        
        # 解析流式响应
        tool_calls_buffer = []
        current_tool_call = None
        
        async for chunk in response:  # type: ignore[var-annotated]
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            finish_reason = chunk.get("choices", [{}])[0].get("finish_reason")
            
            # 处理内容
            if delta.get("content"):
                yield StreamChunk(
                    is_content=True,
                    content=delta["content"],
                )
            
            # 处理 reasoning_content (DeepSeek 等模型)
            if delta.get("reasoning_content"):
                yield StreamChunk(
                    is_reasoning=True,
                    reasoning_content=delta["reasoning_content"],
                )
            
            # 处理工具调用
            if delta.get("tool_calls"):
                for tc in delta["tool_calls"]:
                    tc_id = tc.get("id")
                    tc_function = tc.get("function", {})
                    
                    if tc_id:
                        # 新的工具调用开始
                        # current_tool_call = {
                        #     "id": tc_id,
                        #     "name": tc_function.get("name", ""),
                        #     "arguments": tc_function.get("arguments", ""),
                        # }
                        current_tool_call =StreamToolCallDict(
                            id=tc_id,
                            name=tc_function.get("name", ""),
                            arguments=tc_function.get("arguments", ""),
                        )
                        tool_calls_buffer.append(current_tool_call)
                    elif current_tool_call and tc_function.get("arguments"):
                        # 追加参数
                        current_tool_call["arguments"] += tc_function["arguments"]
            
            # 处理完成
            if finish_reason:
                # 发送工具调用
                for tc in tool_calls_buffer:
                    # 解析参数 JSON
                    try:
                        args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    
                    yield StreamChunk(
                        is_tool_call=True,
                        tool_call=StreamToolCallDict(
                            id=tc["id"],
                            name=tc["name"],
                            arguments=args,
                        ),
                    )
                
                yield StreamChunk(
                    is_done=True,
                    finish_reason=finish_reason,
                )


def create_provider_from_env() -> Optional[LiteLLMProvider]:
    """
    从环境变量创建 Provider
    
    检查的环境变量:
    - ANTHROPIC_API_KEY -> 使用 Claude
    - OPENAI_API_KEY -> 使用 GPT
    - DEEPSEEK_API_KEY -> 使用 DeepSeek
    
    Returns:
        LiteLLMProvider 实例，或 None（如果没有配置）
    """
    # 优先级: Anthropic > OpenAI > DeepSeek
    if os.getenv("ANTHROPIC_API_KEY"):
        return LiteLLMProvider(
            model="claude-sonnet-4-6",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            base_url=os.getenv("ANTHROPIC_BASE_URL"),
            default_model="claude-sonnet-4-6",
        )
    
    if os.getenv("OPENAI_API_KEY"):
        return LiteLLMProvider(
            model="gpt-4",
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            default_model="gpt-4",
        )
    
    if os.getenv("DEEPSEEK_API_KEY"):
        return LiteLLMProvider(
            model="deepseek/deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            # Do NOT pass base_url — litellm routes deepseek/ prefix automatically
            default_model="deepseek/deepseek-chat",
        )
    
    return None
