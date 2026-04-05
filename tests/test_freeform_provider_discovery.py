"""
自由组合 Provider 发现测试
通过任意 API key + URL 组合测试连通性，发现所有可用配置
"""

import asyncio
import json
import os
import re
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

# 忽略 LangChain 弃用警告
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*ChatLiteLLM.*deprecated.*")

# 设置日志级别减少输出
import logging
logging.getLogger("litellm").setLevel(logging.ERROR)
logging.getLogger("langchain").setLevel(logging.WARNING)

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
class Credential:
    """API 凭证"""
    key_var: str          # 环境变量名，如 MY_CUSTOM_API_KEY
    api_key: str          # key 值
    url_var: Optional[str]  # 对应的 URL 变量名
    base_url: Optional[str]  # URL 值


@dataclass
class TestConfig:
    """测试配置"""
    credential: Credential
    model_format: str     # 模型名称格式
    api_format: str       # anthropic 或 openai


@dataclass
class TestResult:
    """测试结果"""
    config: TestConfig
    success: bool
    error: Optional[str] = None
    response_time_ms: Optional[float] = None


def discover_all_credentials() -> list[Credential]:
    """从 .env 文件发现所有配置的 API key（排除注释）"""
    credentials = []

    # 从 .env 文件读取，只获取非注释的配置
    env_path = Path(__file__).resolve().parent.parent / ".env"
    configured_keys = {}  # key_name -> (value, is_commented)

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line_stripped = line.strip()
                if not line_stripped or "=" not in line:
                    continue

                # 检查是否是注释行
                is_commented = line_stripped.startswith("#")
                if is_commented:
                    # 移除开头的 # 和空格以获取实际的 key
                    line_content = line_stripped[1:].strip()
                else:
                    line_content = line_stripped

                if "=" not in line_content:
                    continue

                key, value = line_content.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if key and value and key.endswith("_API_KEY"):
                    # 只保存非注释的配置
                    if not is_commented:
                        configured_keys[key] = value

    # 为每个配置的 key 创建 Credential
    for key, value in configured_keys.items():
        base_key = key.replace("_API_KEY", "")
        url_var = f"{base_key}_BASE_URL"

        # 从 .env 读取对应的 URL（也检查是否注释）
        base_url = None
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_stripped = line.strip()
                    if line_stripped.startswith(url_var + "="):
                        # 非注释行
                        _, url_val = line_stripped.split("=", 1)
                        base_url = url_val.strip().strip('"').strip("'")
                        break
                    elif line_stripped.startswith("#" + url_var + "=") or line_stripped.startswith("# " + url_var + "="):
                        # 注释掉的 URL，跳过
                        continue

        # 如果 .env 中没有配置 URL，尝试从环境变量读取
        if not base_url:
            base_url = os.getenv(url_var)

        credentials.append(Credential(
            key_var=key,
            api_key=value,
            url_var=url_var if base_url else None,
            base_url=base_url,
        ))

    return credentials


def generate_test_models() -> list[tuple[str, str]]:
    """生成要测试的模型名称和 API 格式组合"""
    test_cases = []

    # 常见模型名称（不带前缀）
    model_names = [
        "deepseek-chat",
        "deepseek-reasoner",
        "claude-sonnet-4-6",
        "claude-opus-4-6",
        "gpt-4o",
        "gpt-4o-mini",
        "kimi-k2-coding",
        "kimi-k2.5",
    ]

    # 常见 provider 前缀
    providers = [
        ("deepseek", "openai"),
        ("anthropic", "anthropic"),
        ("openai", "openai"),
        ("kimi", "openai"),
    ]

    for model in model_names:
        # 不带前缀
        test_cases.append((model, "openai"))
        test_cases.append((model, "anthropic"))

        # 带前缀
        for provider, api_fmt in providers:
            test_cases.append((f"{provider}/{model}", api_fmt))

    return test_cases


def detect_api_format_from_url(base_url: Optional[str]) -> Optional[str]:
    """从 URL 检测 API 格式"""
    if not base_url:
        return None

    url_lower = base_url.lower()

    # anthropic 格式特征
    if ".anthropic.com" in url_lower:
        return "anthropic"

    # OpenAI 兼容格式（大多数国内厂商）
    return "openai"


async def test_single_config(config: TestConfig) -> TestResult:
    """测试单个配置组合"""
    import time

    start_time = time.time()

    try:
        # 导入并设置 verbose=False 减少输出
        from langchain_community.chat_models import ChatLiteLLM
        import litellm
        litellm.suppress_debug_info = True
        litellm.set_verbose = False

        # 根据 api_format 调整参数
        kwargs = {
            "model": config.model_format,
            "api_key": config.credential.api_key,
            "temperature": 0.7,
            "verbose": False,
        }

        if config.credential.base_url:
            kwargs["api_base"] = config.credential.base_url

        # anthropic 格式需要特殊处理
        if config.api_format == "anthropic":
            # LiteLLM 通过 model 名称前缀识别 provider
            pass  # model 名称已包含前缀

        test_model = ChatLiteLLM(**kwargs)

        messages = [{"role": "user", "content": "Hi, respond with OK"}]

        # 尝试流式调用
        chunks_received = 0
        async for chunk in test_model.astream(messages):
            chunks_received += 1
            if chunks_received >= 1:
                break

        elapsed = (time.time() - start_time) * 1000

        return TestResult(
            config=config,
            success=True,
            response_time_ms=elapsed,
        )

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        return TestResult(
            config=config,
            success=False,
            error=str(e)[:200],
            response_time_ms=elapsed,
        )


async def discover_all_working_configs() -> dict:
    """发现所有可用的配置组合"""

    print("=" * 70)
    print("自由组合 Provider 发现测试")
    print("=" * 70)

    # 发现所有凭证
    credentials = discover_all_credentials()
    print(f"\n发现 {len(credentials)} 个 API key:")
    for cred in credentials:
        print(f"  - {cred.key_var}")
        if cred.base_url:
            print(f"    URL: {cred.base_url}")
        else:
            print(f"    URL: (default)")

    # 生成测试配置组合
    test_models = generate_test_models()

    all_configs = []
    for cred in credentials:
        # 从 URL 检测 API 格式
        detected_format = detect_api_format_from_url(cred.base_url)

        for model, default_fmt in test_models:
            # 如果检测到格式，优先使用；否则使用默认
            api_fmt = detected_format or default_fmt

            all_configs.append(TestConfig(
                credential=cred,
                model_format=model,
                api_format=api_fmt,
            ))

    print(f"\n将测试 {len(all_configs)} 个配置组合...")

    # 并行测试（限制并发数避免被封）
    semaphore = asyncio.Semaphore(5)

    async def bounded_test(config):
        async with semaphore:
            return await test_single_config(config)

    results = await asyncio.gather(*[bounded_test(cfg) for cfg in all_configs])

    # 整理结果
    working_configs = []
    failed_tests = []

    for result in results:
        cred = result.config.credential
        model = result.config.model_format

        if result.success:
            working_configs.append({
                "key_var": cred.key_var,
                "api_key_preview": f"{cred.api_key[:10]}...",
                "base_url": cred.base_url,
                "working_model": model,
                "api_format": result.config.api_format,
                "response_time_ms": round(result.response_time_ms, 2),
            })
        else:
            # 只记录有代表性的失败
            key = (cred.key_var, model)
            failed_tests.append({
                "key_var": cred.key_var,
                "model": model,
                "api_format": result.config.api_format,
                "error": result.error,
            })

    # 按 key_var 分组，保留所有可用的模型配置
    configs_by_key = {}
    for cfg in working_configs:
        key = cfg["key_var"]
        if key not in configs_by_key:
            configs_by_key[key] = []
        configs_by_key[key].append(cfg)

    # 为每个 key 选择最快的配置作为代表，但保留所有信息
    best_configs = {}
    all_working_unique = []
    for key, configs in configs_by_key.items():
        # 按响应时间排序
        configs.sort(key=lambda x: x["response_time_ms"])
        best_configs[key] = configs[0]  # 最快的作为代表
        all_working_unique.extend(configs)  # 保留所有

    # 输出结果
    print("\n" + "=" * 70)
    print("测试结果")
    print("=" * 70)

    total_working = len(all_working_unique)
    if best_configs:
        print(f"\n✓ 找到 {total_working} 个可用配置 (来自 {len(best_configs)} 个 API key):")
        # 显示每个 key 的所有可用模型
        for key, configs in configs_by_key.items():
            print(f"\n  [{key}] - {len(configs)} 个可用模型")
            print(f"    URL: {configs[0]['base_url'] or '(default)'}")
            for i, cfg in enumerate(configs[:10], 1):  # 显示前10个
                print(f"      {i}. {cfg['working_model']} ({cfg['api_format']}, {cfg['response_time_ms']}ms)")
            if len(configs) > 10:
                print(f"      ... 还有 {len(configs) - 10} 个")
    else:
        print("\n✗ 未找到可用配置")

    # 保存结果
    project_root = Path(__file__).resolve().parent.parent
    logs_dir = project_root / "logs" / "connectivity"
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    result = {
        "timestamp": datetime.now().isoformat(),
        "credentials_found": len(credentials),
        "total_tests": len(all_configs),
        "working_configs": list(best_configs.values()),
        "all_working": working_configs,
        "sample_failures": failed_tests[:10],
    }

    result_file = logs_dir / f"freeform_discovery_{ts}.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {result_file.name}")

    return result


async def main():
    """主函数"""
    result = await discover_all_working_configs()

    # 生成推荐配置
    print("\n" + "=" * 70)
    print("推荐配置")
    print("=" * 70)

    # 按 key_var 分组显示所有可用配置
    configs_by_key = {}
    for cfg in result["all_working"]:
        key = cfg['key_var']
        if key not in configs_by_key:
            configs_by_key[key] = []
        configs_by_key[key].append(cfg)

    for key, configs in configs_by_key.items():
        print(f"\n# {key} ({len(configs)} 个可用模型)")
        print(f"{key}={os.getenv(key)}")
        if configs[0]['base_url']:
            print(f"{key.replace('_API_KEY', '_BASE_URL')}={configs[0]['base_url']}")
        print(f"# 可用模型列表:")
        for cfg in configs:
            print(f"#   - {cfg['working_model']}")
        print(f"# 推荐配置 (最快响应):")
        print(f"MODEL_ID={configs[0]['working_model']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
