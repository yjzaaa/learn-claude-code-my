"""
测试 ChatLiteLLM 模型 API 联通性
验证 ChatLiteLLM 是否能正确调用不同 provider 的模型
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

# 手动加载项目根目录的 .env 文件（强制覆盖现有环境变量）
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

# 清除错误的中文占位符 token
os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

# 设置日志
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _default_json(obj):
    """json.dumps 的 default 回调"""
    from langchain_core.messages import BaseMessage, message_to_dict
    if isinstance(obj, BaseMessage):
        return message_to_dict(obj)
    try:
        return dict(obj)
    except Exception:
        return str(obj)


async def test_chatlitellm_connectivity():
    """测试 ChatLiteLLM 联通性"""

    try:
        from langchain_community.chat_models import ChatLiteLLM
    except ImportError as e:
        print(f"错误: 缺少 langchain_community: {e}")
        print("请安装: pip install langchain-community")
        return None

    # 从环境变量获取配置
    model_name = os.getenv("MODEL_ID", "deepseek/deepseek-chat")
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL") or os.getenv("OPENAI_BASE_URL")

    # 根据 model_name 推断 base_url
    if not base_url:
        if "deepseek" in model_name.lower():
            base_url = "https://api.deepseek.com/v1"
        elif "claude" in model_name.lower():
            base_url = "https://api.anthropic.com/v1"
        elif "gpt" in model_name.lower():
            base_url = "https://api.openai.com/v1"

    print(f"\n{'='*60}")
    print("测试 ChatLiteLLM 联通性")
    print(f"{'='*60}")
    print(f"model={model_name}")
    print(f"base_url={base_url}")
    print(f"api_key_set={bool(api_key)}")

    if not api_key:
        print("错误: 未找到 API key")
        return None

    # 创建日志目录
    project_root = Path(__file__).resolve().parent.parent
    logs_dir = project_root / "logs" / "connectivity"
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = logs_dir / f"chatlitellm_{ts}.jsonl"

    print("\n初始化 ChatLiteLLM...")

    try:
        model = ChatLiteLLM(
            model=model_name,
            api_key=api_key,
            api_base=base_url,
            temperature=0.7,
        )
        print("✓ ChatLiteLLM 初始化成功")
    except Exception as e:
        print(f"✗ ChatLiteLLM 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    messages = [{"role": "user", "content": "你好，请用一句话介绍自己"}]

    print("\n开始流式调用...")
    print(f"输出文件: {output_file}")
    print(f"{'='*60}\n")

    event_count = 0
    full_content = ""
    error_occurred = None

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            async for chunk in model.astream(messages):
                event_count += 1
                content = getattr(chunk, "content", str(chunk))
                full_content += content

                record = {
                    "index": event_count,
                    "timestamp": datetime.now().isoformat(),
                    "content": content,
                    "type": getattr(chunk, "type", None),
                }
                line = json.dumps(record, ensure_ascii=False, default=_default_json)
                f.write(line + "\n")
                print(f"[{event_count}] {content!r}")

    except Exception as e:
        error_occurred = str(e)
        print(f"\n✗ 流式调用失败: {e}")
        import traceback
        traceback.print_exc()

    # 写入汇总信息
    summary_file = logs_dir / f"chatlitellm_{ts}_summary.json"
    summary = {
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "base_url": base_url,
        "api_key_set": bool(api_key),
        "total_chunks": event_count,
        "full_content": full_content,
        "error": error_occurred,
        "status": "success" if not error_occurred and event_count > 0 and full_content.strip() else "failed",
    }

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print("测试结果")
    print(f"{'='*60}")
    print(f"总事件数: {event_count}")
    print(f"完整回复: {full_content}")
    print(f"输出文件: {output_file.name}")
    print(f"汇总文件: {summary_file.name}")
    print(f"联通性状态: {summary['status']}")
    print(f"{'='*60}\n")

    return summary['status'] == 'success'


async def test_chatlitellm_with_provider_manager():
    """使用 ProviderManager 配置测试 ChatLiteLLM"""

    try:
        from langchain_community.chat_models import ChatLiteLLM

        from backend.infrastructure.services import ProviderManager
    except ImportError as e:
        print(f"错误: 缺少依赖: {e}")
        return None

    print(f"\n{'='*60}")
    print("使用 ProviderManager 测试 ChatLiteLLM")
    print(f"{'='*60}")

    provider_mgr = ProviderManager()
    model_config = provider_mgr.get_model_config()

    print(f"model={model_config.model}")
    print(f"provider={model_config.provider}")
    print(f"base_url={model_config.base_url}")
    print(f"api_key_set={bool(model_config.api_key)}")

    if not model_config.api_key:
        print("错误: ProviderManager 未找到 API key")
        return None

    project_root = Path(__file__).resolve().parent.parent
    logs_dir = project_root / "logs" / "connectivity"
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = logs_dir / f"chatlitellm_pm_{ts}.jsonl"

    try:
        model = ChatLiteLLM(
            model=model_config.model,
            api_key=model_config.api_key,
            api_base=model_config.base_url,
            temperature=0.7,
        )
        print("✓ ChatLiteLLM 初始化成功")
    except Exception as e:
        print(f"✗ ChatLiteLLM 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    messages = [{"role": "user", "content": "Hello, introduce yourself in one sentence"}]

    print("\n开始流式调用...")
    event_count = 0
    full_content = ""

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            async for chunk in model.astream(messages):
                event_count += 1
                content = getattr(chunk, "content", str(chunk))
                full_content += content

                record = {
                    "index": event_count,
                    "timestamp": datetime.now().isoformat(),
                    "content": content,
                    "type": getattr(chunk, "type", None),
                }
                line = json.dumps(record, ensure_ascii=False, default=_default_json)
                f.write(line + "\n")
                print(f"[{event_count}] {content!r}")

        print("\n✓ 流式调用成功")
        print(f"总事件数: {event_count}")
        print(f"完整回复: {full_content}")

    except Exception as e:
        print(f"\n✗ 流式调用失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    return True


async def main():
    """主函数：运行所有测试"""

    print("\n" + "="*60)
    print("ChatLiteLLM 联通性测试")
    print("="*60)

    # 测试 1: 直接使用环境变量
    result1 = await test_chatlitellm_connectivity()

    # 测试 2: 使用 ProviderManager
    result2 = await test_chatlitellm_with_provider_manager()

    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)
    print(f"环境变量测试: {'✓ PASS' if result1 else '✗ FAIL'}")
    print(f"ProviderManager 测试: {'✓ PASS' if result2 else '✗ FAIL'}")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
