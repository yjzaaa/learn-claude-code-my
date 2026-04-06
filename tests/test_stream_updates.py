"""
测试 stream_mode="updates" 的行为
"""
import asyncio
import os
from pathlib import Path

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

async def test():
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend
    from langchain_anthropic import ChatAnthropic
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.store.memory import InMemoryStore

    model = ChatAnthropic(
        model=os.getenv("MODEL_ID", "kimi-k2-coding"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        anthropic_api_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.kimi.com/coding/"),
        temperature=0.7,
    )

    backend = FilesystemBackend(root_dir=".", virtual_mode=True)
    agent = create_deep_agent(
        name="test",
        model=model,
        tools=[],
        system_prompt="你是助手，简洁回答。",
        backend=backend,
        checkpointer=MemorySaver(),
        store=InMemoryStore(),
        skills=[],
        subagents=[],
        interrupt_on={},
    )

    messages = [{"role": "user", "content": "你好"}]
    config = {"configurable": {"thread_id": "test_updates_001"}}

    print("=== stream_mode='updates' ===")
    count = 0
    async for raw_event in agent.astream(
        {"messages": messages},
        config,
        stream_mode="updates"
    ):
        count += 1
        print(f"\n--- Event {count} ---")
        print(f"Type: {type(raw_event)}")
        if isinstance(raw_event, dict):
            for node_name, state_update in raw_event.items():
                print(f"Node: {node_name}")
                print(f"State update type: {type(state_update)}")
                print(f"State update keys: {list(state_update.keys()) if hasattr(state_update, 'keys') else 'N/A'}")
                msgs = state_update.get("messages") if hasattr(state_update, "get") else None
                print(f"Messages type: {type(msgs)}")
                if isinstance(msgs, list):
                    for i, m in enumerate(msgs):
                        print(f"  [{i}] {type(m).__name__}: {getattr(m, 'content', '')[:80]!r}")
                elif msgs is not None:
                    print(f"  Messages repr: {repr(msgs)[:500]}")
        else:
            print(f"Raw: {raw_event}")

if __name__ == "__main__":
    asyncio.run(test())
