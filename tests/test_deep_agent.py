"""
测试 create_deep_agent 运行情况
使用 .env 中的 ANTHROPIC_ 配置
stream_mode="updates" 直接产出节点级状态更新，包含完整 AIMessage
裸 raw_event 直接写入 jsonl，不做任何包装
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


def _serialize_messages(obj):
    """序列化 LangGraph 状态中的 messages（兼容 list / Overwrite）"""
    from langchain_core.messages import BaseMessage, message_to_dict
    # 处理 LangGraph Overwrite 包装
    if hasattr(obj, "value"):
        obj = obj.value
    if isinstance(obj, list):
        return [message_to_dict(m) if isinstance(m, BaseMessage) else str(m) for m in obj]
    return str(obj)


def _default_json(obj):
    """json.dumps 的 default 回调"""
    from langchain_core.messages import BaseMessage, message_to_dict
    if isinstance(obj, BaseMessage):
        return message_to_dict(obj)
    # 兼容 Overwrite
    if hasattr(obj, "value"):
        return _serialize_messages(obj)
    try:
        return dict(obj)
    except Exception:
        return str(obj)


async def test_deep_agent():
    """测试 Deep Agent，使用 stream_mode='updates'，裸写入 jsonl"""

    try:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.store.memory import InMemoryStore
        from langchain_anthropic import ChatAnthropic
    except ImportError as e:
        print(f"错误: 缺少依赖: {e}")
        return

    model_name = os.getenv("MODEL_ID", "kimi-k2-coding")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.kimi.com/coding/")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    model = ChatAnthropic(
        model=model_name,
        api_key=api_key,
        anthropic_api_url=base_url,
        temperature=0.7,
    )

    name = "test-agent"
    system_prompt = "你是一个有帮助的助手。请简洁地回答用户的问题。"

    checkpointer = MemorySaver()
    store = InMemoryStore()
    backend = FilesystemBackend(root_dir=".", virtual_mode=True)

    print(f"创建 Deep Agent: name={name}, model={model_name}")
    print(f"ANTHROPIC_BASE_URL={base_url}")
    print(f"api_key: {api_key}")

    agent = create_deep_agent(
        name=name,
        model=model,
        tools=[],
        system_prompt=system_prompt,
        backend=backend,
        checkpointer=checkpointer,
        store=store,
        skills=[],
        subagents=[],
        interrupt_on={},
    )

    messages = [{"role": "user", "content": "你好，请介绍一下自己"}]
    config = {"configurable": {"thread_id": "test_dialog_001"}}

    project_root = Path(__file__).resolve().parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    events_file = logs_dir / f"deep_agent_updates_{ts}.jsonl"

    print(f"Events 输出: {events_file}")

    event_count = 0

    with open(events_file, "w", encoding="utf-8") as f_events:
        async for raw_event in agent.astream(
            {"messages": messages},
            config,
            stream_mode="updates"
        ):
            event_count += 1
            line = json.dumps(raw_event, ensure_ascii=False, default=_default_json)
            f_events.write(line + "\n")
            # 同时控制台打印关键节点信息，方便观察
            if isinstance(raw_event, dict):
                for node_name, state_update in raw_event.items():
                    msgs = None
                    if isinstance(state_update, dict):
                        raw_msgs = state_update.get("messages")
                        if raw_msgs is not None:
                            msgs = _serialize_messages(raw_msgs)
                    print(f"[{event_count}] node={node_name} messages_count={len(msgs) if isinstance(msgs, list) else 'N/A'}")

    print(f"流结束")
    print(f"总事件数: {event_count}")
    print(f"输出文件: {events_file.name}")


if __name__ == "__main__":
    asyncio.run(test_deep_agent())
