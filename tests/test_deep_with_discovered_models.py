"""
测试 deep.py 是否可以直接使用 discovery 测试返回的模型配置
验证发现的模型配置在 deep.py 中是否可用
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

# 加载 .env
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ[key] = value

os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _try_chatlitellm(model_name: str, api_key: str, base_url: str):
    """尝试使用 ChatLiteLLM"""
    import litellm
    from langchain_community.chat_models import ChatLiteLLM
    litellm.suppress_debug_info = True

    kwargs = {
        "model": model_name,
        "api_key": api_key,
        "temperature": 0.7,
    }
    if base_url:
        kwargs["api_base"] = base_url

    model = ChatLiteLLM(**kwargs)
    return model


async def _try_chatanthropic(model_name: str, api_key: str, base_url: str):
    """尝试使用 ChatAnthropic"""
    from langchain_anthropic import ChatAnthropic

    # 清理模型名称中的 provider 前缀
    clean_model = model_name.replace("anthropic/", "").replace("openai/", "")

    model = ChatAnthropic(
        model=clean_model,
        api_key=api_key,
        anthropic_api_url=base_url,
        temperature=0.7,
    )
    return model


async def _test_model_streaming(model) -> tuple[bool, str]:
    """测试模型流式调用，返回 (success, response_or_error)"""
    messages = [{"role": "user", "content": "Say 'OK' and nothing else"}]

    response_chunks = []
    async for chunk in model.astream(messages):
        content = getattr(chunk, "content", str(chunk))
        if content:
            response_chunks.append(content)

    full_response = "".join(response_chunks).strip()
    return bool(full_response), full_response


async def test_model_in_deep_context(model_config: dict) -> dict:
    """在 deep.py 的上下文中测试单个模型配置"""

    result = {
        "model": model_config["working_model"],
        "key_var": model_config["key_var"],
        "base_url": model_config["base_url"],
        "success": False,
        "error": None,
        "test_message": None,
    }

    model_name = model_config["working_model"]
    api_key = os.getenv(model_config["key_var"])
    base_url = model_config["base_url"]
    api_format = model_config["api_format"]

    print(f"\n  测试模型: {model_name}")
    print(f"    API Key: {model_config['key_var']}")
    print(f"    Base URL: {base_url or '(default)'}")
    print(f"    API Format: {api_format}")

    # 步骤 1: 尝试 ChatLiteLLM
    model = None
    try:
        print("    尝试 ChatLiteLLM...")
        model = await _try_chatlitellm(model_name, api_key, base_url)
        print("    ✓ ChatLiteLLM 初始化成功")
    except Exception as e:
        print(f"    ✗ ChatLiteLLM 初始化失败: {e}")
        # 初始化失败，直接尝试 ChatAnthropic
        model = None

    # 如果初始化成功，尝试流式调用
    if model:
        try:
            print("    发送测试消息 (ChatLiteLLM)...")
            success, response = await _test_model_streaming(model)
            if success:
                print(f"    ✓ 收到响应: {response[:50]}...")
                result["success"] = True
                result["test_message"] = response
                result["client_type"] = "ChatLiteLLM"
                return result
            print("    ✗ 响应为空，尝试 ChatAnthropic...")
        except Exception as e:
            print(f"    ✗ ChatLiteLLM 流式调用失败: {e}")
            print("    尝试 ChatAnthropic...")

    # 步骤 2: 尝试 ChatAnthropic（适用于 anthropic 格式或 kimi）
    should_try_anthropic = (
        api_format == "anthropic" or
        "claude" in model_name.lower() or
        "kimi" in model_name.lower()
    )

    if should_try_anthropic:
        try:
            print("    尝试 ChatAnthropic...")
            model = await _try_chatanthropic(model_name, api_key, base_url)
            print("    ✓ ChatAnthropic 初始化成功")
        except Exception as e:
            print(f"    ✗ ChatAnthropic 初始化失败: {e}")
            result["error"] = f"ChatLiteLLM failed, ChatAnthropic init failed: {e}"
            return result

        # 尝试流式调用
        try:
            print("    发送测试消息 (ChatAnthropic)...")
            success, response = await _test_model_streaming(model)
            if success:
                print(f"    ✓ 收到响应: {response[:50]}...")
                result["success"] = True
                result["test_message"] = response
                result["client_type"] = "ChatAnthropic"
                return result
            print("    ✗ 响应为空")
            result["error"] = "Empty response from ChatAnthropic"
            return result
        except Exception as e:
            print(f"    ✗ ChatAnthropic 流式调用失败: {e}")
            result["error"] = f"ChatAnthropic streaming failed: {e}"
            return result
    else:
        result["error"] = "ChatLiteLLM failed and model not suitable for ChatAnthropic"
        return result

    return result


async def test_all_discovered_models():
    """测试所有发现的模型配置"""

    print("=" * 70)
    print("Deep.py 模型配置兼容性测试")
    print("=" * 70)

    # 首先运行 discovery 测试获取可用配置
    print("\n步骤 1: 运行 Provider Discovery...")

    # 导入 discovery 函数
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from tests.test_freeform_provider_discovery import (
        detect_api_format_from_url,
        discover_all_credentials,
    )

    credentials = discover_all_credentials()
    print(f"  发现 {len(credentials)} 个 API key")

    # 为每个 credential 选择代表性的模型进行测试
    test_configs = []

    for cred in credentials:
        # 根据 URL 推断 provider
        actual_provider = detect_api_format_from_url(cred.base_url) or cred.key_var.replace("_API_KEY", "").lower()

        # 为每个 key 选择几个代表性的模型格式
        models_to_test = []

        if "deepseek" in actual_provider.lower() or (cred.base_url and "deepseek" in cred.base_url.lower()):
            models_to_test = [
                ("deepseek/deepseek-chat", "openai"),
                ("deepseek/deepseek-reasoner", "openai"),
            ]
        elif "anthropic" in actual_provider.lower() or (cred.base_url and "anthropic" in cred.base_url.lower()):
            models_to_test = [
                ("anthropic/claude-sonnet-4-6", "anthropic"),
                ("claude-sonnet-4-6", "anthropic"),
            ]
        elif "kimi" in actual_provider.lower() or (cred.base_url and "kimi" in cred.base_url.lower()):
            models_to_test = [
                ("openai/kimi-k2-coding", "openai"),
                ("kimi-k2-coding", "openai"),
            ]
        else:
            # 通用测试
            models_to_test = [
                (f"{actual_provider}/test-model", "openai"),
            ]

        for model, api_fmt in models_to_test:
            test_configs.append({
                "key_var": cred.key_var,
                "api_key": cred.api_key,
                "base_url": cred.base_url,
                "working_model": model,
                "api_format": api_fmt,
            })

    print(f"\n步骤 2: 测试 {len(test_configs)} 个模型配置...")

    # 并行测试
    results = []
    for config in test_configs:
        result = await test_model_in_deep_context(config)
        results.append(result)
        # 间隔避免限流
        await asyncio.sleep(0.5)

    # 整理结果
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)

    print(f"\n✓ 成功: {len(successful)}/{len(results)}")
    for r in successful:
        print(f"  - {r['model']} ({r['key_var']})")
        print(f"    响应: {r['test_message'][:50]}...")

    if failed:
        print(f"\n✗ 失败: {len(failed)}/{len(results)}")
        for r in failed:
            print(f"  - {r['model']} ({r['key_var']})")
            print(f"    错误: {r['error'][:100]}...")

    # 保存结果
    project_root = Path(__file__).resolve().parent.parent
    logs_dir = project_root / "logs" / "connectivity"
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    result_data = {
        "timestamp": datetime.now().isoformat(),
        "total_tested": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "working_configs": successful,
        "failed_configs": failed,
    }

    result_file = logs_dir / f"deep_model_test_{ts}.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {result_file.name}")

    # 生成可直接使用的配置
    print("\n" + "=" * 70)
    print("可直接使用的 MODEL_ID 配置")
    print("=" * 70)

    for r in successful:
        print(f"\n# {r['key_var']}")
        print(f"MODEL_ID={r['model']}")
        if r['base_url']:
            print(f"{r['key_var'].replace('_API_KEY', '_BASE_URL')}={r['base_url']}")

    print("\n" + "=" * 70)

    return result_data


if __name__ == "__main__":
    asyncio.run(test_all_discovered_models())
