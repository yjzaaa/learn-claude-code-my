"""
Provider 发现测试 - 并行测试 API key 与 URL 组合
自动发现可用的模型配置列表
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# 加载 .env
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ[key] = value


@dataclass
class ProviderConfig:
    """Provider 配置"""
    key_name: str  # 如 ANTHROPIC_API_KEY
    api_key: str
    base_url: Optional[str]
    inferred_provider: str  # 从 key_name 推断的 provider
    actual_provider: str  # 从 base_url 检测的实际 provider


@dataclass
class TestResult:
    """测试结果"""
    provider_config: ProviderConfig
    model_name: str
    test_model_with_prefix: str  # 带 provider 前缀的模型名
    success: bool
    error: Optional[str] = None
    response_time_ms: Optional[float] = None


# Provider 默认配置
PROVIDER_DEFAULTS = {
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "test_model": "claude-sonnet-4-6",
        "prefix": "anthropic",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "test_model": "deepseek-chat",
        "prefix": "deepseek",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "test_model": "gpt-4o",
        "prefix": "openai",
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "test_model": "kimi-k2-coding",
        "prefix": "openai",  # Kimi 使用 OpenAI 兼容格式
    },
}


def detect_provider_from_key(key_name: str) -> str:
    """从 API key 名称推断 provider"""
    key_lower = key_name.lower()
    if "anthropic" in key_lower:
        return "anthropic"
    if "deepseek" in key_lower:
        return "deepseek"
    if "openai" in key_lower:
        return "openai"
    if "kimi" in key_lower or "moonshot" in key_lower:
        return "kimi"
    return "unknown"


def detect_provider_from_url(base_url: str) -> str:
    """从 base_url 检测实际 provider"""
    url_lower = base_url.lower()
    if "kimi" in url_lower or "moonshot" in url_lower:
        return "kimi"
    if "deepseek" in url_lower:
        return "deepseek"
    if "anthropic" in url_lower:
        return "anthropic"
    if "openai" in url_lower and "azure" not in url_lower:
        return "openai"
    return "unknown"


def get_all_provider_configs() -> list[ProviderConfig]:
    """获取所有配置的 provider"""
    configs = []

    # 检查所有可能的 API key
    api_key_mappings = [
        ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"),
        ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"),
        ("OPENAI_API_KEY", "OPENAI_BASE_URL"),
        ("KIMI_API_KEY", "KIMI_BASE_URL"),
    ]

    for key_name, url_name in api_key_mappings:
        api_key = os.getenv(key_name)
        if api_key:
            base_url = os.getenv(url_name)
            inferred = detect_provider_from_key(key_name)
            actual = detect_provider_from_url(base_url) if base_url else inferred

            configs.append(ProviderConfig(
                key_name=key_name,
                api_key=api_key,
                base_url=base_url,
                inferred_provider=inferred,
                actual_provider=actual if actual != "unknown" else inferred,
            ))

    return configs


async def test_provider_connectivity(config: ProviderConfig) -> list[TestResult]:
    """测试单个 provider 配置的连通性"""
    results = []

    # 确定测试模型（带和不带前缀）
    provider_info = PROVIDER_DEFAULTS.get(config.actual_provider, {})
    test_model = provider_info.get("test_model", "unknown")
    prefix = provider_info.get("prefix", config.actual_provider)

    # 测试带前缀的模型名
    test_models = [
        f"{prefix}/{test_model}",  # 带前缀
        test_model,  # 不带前缀
    ]

    for model in test_models:
        result = await _test_single_model(config, model)
        results.append(result)
        if result.success:
            # 如果成功了，不需要测试其他格式
            break

    return results


async def _test_single_model(config: ProviderConfig, model: str) -> TestResult:
    """测试单个模型"""
    import time

    start_time = time.time()

    try:
        from langchain_community.chat_models import ChatLiteLLM

        test_model = ChatLiteLLM(
            model=model,
            api_key=config.api_key,
            api_base=config.base_url,
            temperature=0.7,
        )

        messages = [{"role": "user", "content": "Hi"}]

        # 尝试一次简单的调用
        async for chunk in test_model.astream(messages):
            # 只要能收到第一个 chunk 就算成功
            break

        elapsed = (time.time() - start_time) * 1000

        return TestResult(
            provider_config=config,
            model_name=config.actual_provider,
            test_model_with_prefix=model,
            success=True,
            response_time_ms=elapsed,
        )

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        return TestResult(
            provider_config=config,
            model_name=config.actual_provider,
            test_model_with_prefix=model,
            success=False,
            error=str(e),
            response_time_ms=elapsed,
        )


async def discover_available_providers() -> dict:
    """发现并返回所有可用的 provider 配置"""

    print("=" * 70)
    print("Provider 发现测试")
    print("=" * 70)

    # 获取所有配置的 provider
    configs = get_all_provider_configs()
    print(f"\n找到 {len(configs)} 个配置的 provider:")
    for cfg in configs:
        print(f"  - {cfg.key_name}: {cfg.inferred_provider} -> {cfg.actual_provider}")
        print(f"    URL: {cfg.base_url or 'default'}")

    # 并行测试所有 provider
    print(f"\n开始并行测试...")
    tasks = [test_provider_connectivity(cfg) for cfg in configs]
    all_results = await asyncio.gather(*tasks)

    # 整理结果
    available_providers = []
    failed_providers = []

    for results in all_results:
        for result in results:
            if result.success:
                available_providers.append({
                    "key_name": result.provider_config.key_name,
                    "inferred_provider": result.provider_config.inferred_provider,
                    "actual_provider": result.provider_config.actual_provider,
                    "base_url": result.provider_config.base_url,
                    "working_model_format": result.test_model_with_prefix,
                    "response_time_ms": result.response_time_ms,
                })
            else:
                failed_providers.append({
                    "key_name": result.provider_config.key_name,
                    "model": result.test_model_with_prefix,
                    "error": result.error,
                })

    # 输出结果
    print("\n" + "=" * 70)
    print("测试结果")
    print("=" * 70)

    if available_providers:
        print(f"\n✓ 可用 provider ({len(available_providers)} 个):")
        for p in available_providers:
            print(f"  - {p['actual_provider']}")
            print(f"    key: {p['key_name']}")
            print(f"    url: {p['base_url'] or 'default'}")
            print(f"    model format: {p['working_model_format']}")
            print(f"    response: {p['response_time_ms']:.0f}ms")
    else:
        print("\n✗ 没有可用的 provider")

    if failed_providers:
        print(f"\n✗ 失败的测试 ({len(failed_providers)} 个):")
        for f in failed_providers:
            error_short = f['error'][:80] + "..." if len(f['error']) > 80 else f['error']
            print(f"  - {f['key_name']} / {f['model']}: {error_short}")

    # 构建最终配置
    result = {
        "timestamp": datetime.now().isoformat(),
        "total_tested": len(configs),
        "available_count": len(available_providers),
        "available_providers": available_providers,
        "failed_tests": failed_providers,
    }

    # 保存结果
    project_root = Path(__file__).resolve().parent.parent
    logs_dir = project_root / "logs" / "connectivity"
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = logs_dir / f"provider_discovery_{ts}.json"

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {result_file.name}")
    print("=" * 70)

    return result


async def main():
    """主函数"""
    result = await discover_available_providers()

    # 打印可直接使用的配置
    print("\n" + "=" * 70)
    print("推荐配置 (.env 格式)")
    print("=" * 70)

    for provider in result["available_providers"]:
        print(f"\n# {provider['actual_provider'].upper()}")
        print(f"{provider['key_name']}={os.getenv(provider['key_name'])}")
        if provider['base_url']:
            url_key = provider['key_name'].replace('_API_KEY', '_BASE_URL')
            print(f"{url_key}={provider['base_url']}")
        print(f"MODEL_ID={provider['working_model_format']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
