"""LLM Adapter Usage Example - 适配器使用示例

演示如何使用 LLM Response Adapter 统一处理不同提供商的响应。
"""

import asyncio
from backend.infrastructure.llm_adapter import (
    LLMResponseAdapterFactory,
    create_adapter,
    detect_provider,
    StreamingParser,
)


def example_basic_usage():
    """基础使用示例"""
    print("=== 基础使用示例 ===")

    # 创建适配器工厂
    factory = LLMResponseAdapterFactory()

    # 根据模型名称创建适配器
    models = [
        "claude-sonnet-4-6",
        "deepseek-chat",
        "kimi-k2-coding",
        "gpt-4",
    ]

    for model in models:
        adapter = factory.create_adapter(model)
        provider = factory.detect_provider(model)
        print(f"Model: {model} -> Provider: {provider}, Adapter: {adapter.__class__.__name__}")


def example_parse_response():
    """解析响应示例"""
    print("\n=== 解析响应示例 ===")

    # Claude 响应示例
    claude_response = {
        "content": "Hello! How can I help you?",
        "model": "claude-sonnet-4-6",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20,
        },
        "additional_kwargs": {
            "reasoning_content": "The user is greeting me..."
        }
    }

    # 创建 Claude 适配器
    adapter = create_adapter("claude-sonnet-4-6")

    # 解析响应
    parsed = adapter.parse_response(claude_response)

    print(f"Content: {parsed.content}")
    print(f"Reasoning: {parsed.reasoning_content}")
    print(f"Model: {parsed.model}")
    print(f"Provider: {parsed.provider}")
    print(f"Usage: {parsed.usage}")


def example_streaming():
    """流式处理示例"""
    print("\n=== 流式处理示例 ===")

    # 创建适配器和流式解析器
    adapter = create_adapter("deepseek-chat")
    parser = StreamingParser(adapter)

    # 模拟流式 chunks
    chunks = [
        {"delta": {"content": "Hello", "reasoning_content": "Thinking..."}},
        {"delta": {"content": " world", "reasoning_content": " more thinking"}},
        {"choices": [{"delta": {"content": "!", "reasoning_content": ""}, "finish_reason": "stop"}]},
    ]

    for chunk in chunks:
        result = parser.parse_chunk(chunk)

        if result.content_delta:
            print(f"Text delta: {result.content_delta}")
        if result.reasoning_delta:
            print(f"Reasoning delta: {result.reasoning_delta}")

    print(f"\nFinal content: {parser.accumulated_content}")
    print(f"Final reasoning: {parser.accumulated_reasoning}")


def example_token_usage():
    """Token 用量示例"""
    print("\n=== Token 用量示例 ===")

    from backend.infrastructure.llm_adapter import TokenUsage

    # 创建 TokenUsage
    usage = TokenUsage(
        input_tokens=100,
        output_tokens=50,
    )

    print(f"Input tokens: {usage.input_tokens}")
    print(f"Output tokens: {usage.output_tokens}")
    print(f"Total tokens: {usage.total_tokens}")

    # 从 OpenAI 格式创建
    usage2 = TokenUsage.from_openai_format(
        prompt_tokens=200,
        completion_tokens=100,
    )
    print(f"\nFrom OpenAI format - Total: {usage2.total_tokens}")


async def main():
    """主函数"""
    example_basic_usage()
    example_parse_response()
    example_streaming()
    example_token_usage()


if __name__ == "__main__":
    asyncio.run(main())
