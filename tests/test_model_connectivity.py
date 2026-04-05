"""
测试模型 API 联通性
参考 test_deep_agent.py 的写法，直接调用模型并将流式输出写入 jsonl
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

# 手动加载项目根目录的 .env 文件（强制覆盖现有环境变量）
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

# 清除错误的中文占位符 token
os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

# 设置日志
import logging
logging.basicConfig(level=logging.INFO)

# 统一配置来源：ProviderManager（可选导入，失败时回退到环境变量）
try:
    from backend.infrastructure.services import ProviderManager
    _PM_AVAILABLE = True
except ImportError:
    _PM_AVAILABLE = False


def _default_json(obj):
    """json.dumps 的 default 回调"""
    from langchain_core.messages import BaseMessage, message_to_dict
    if isinstance(obj, BaseMessage):
        return message_to_dict(obj)
    try:
        return dict(obj)
    except Exception:
        return str(obj)


async def test_model_connectivity():
    """直接测试模型 API 联通性，流式输出写入 jsonl"""

    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as e:
        print(f"错误: 缺少依赖: {e}")
        return

    # 优先使用 ProviderManager 获取统一配置
    if _PM_AVAILABLE:
        provider_mgr = ProviderManager()
        model_config = provider_mgr.get_model_config()
        model_name = model_config.model
        base_url = model_config.base_url or os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1/")
        api_key = model_config.api_key
        print(f"[ProviderManager] model={model_name}, provider={model_config.provider}")
    else:
        # 回退到环境变量
        model_name = os.getenv("MODEL_ID", "claude-sonnet-4-6")
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1/")
        api_key = os.getenv("ANTHROPIC_API_KEY")

    print(f"测试模型联通性: model={model_name}")
    print(f"ANTHROPIC_BASE_URL={base_url}")
    print(f"api_key_set={bool(api_key)}")

    model = ChatAnthropic(
        model=model_name,
        api_key=api_key,
        anthropic_api_url=base_url,
        temperature=0.7,
    )

    messages = [{"role": "user", "content": "你好，请用一句话介绍自己"}]

    project_root = Path(__file__).resolve().parent.parent
    logs_dir = project_root / "logs" / "connectivity"
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = logs_dir / f"model_connectivity_{ts}.jsonl"

    print(f"开始流式调用，输出文件: {output_file}")

    event_count = 0
    full_content = ""

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

    # 写入汇总信息
    summary_file = logs_dir / f"model_connectivity_{ts}_summary.json"
    summary = {
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "base_url": base_url,
        "api_key_set": bool(api_key),
        "total_chunks": event_count,
        "full_content": full_content,
        "status": "success" if event_count > 0 and full_content.strip() else "failed",
    }
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n流结束")
    print(f"总事件数: {event_count}")
    print(f"完整回复: {full_content}")
    print(f"输出文件: {output_file.name}")
    print(f"汇总文件: {summary_file.name}")
    print(f"联通性状态: {summary['status']}")


if __name__ == "__main__":
    asyncio.run(test_model_connectivity())
