"""
模拟 main.py 的启动路径，验证 DeepAgentRuntime 初始化
"""
import os
from pathlib import Path

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

os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

from core.models.config import EngineConfig
from core.agent.runtime_factory import AgentRuntimeFactory

config = EngineConfig.from_dict({"skills": {"skills_dir": str(_PROJECT_ROOT / "skills")}})
print("EngineConfig provider:", config.provider)
print("MODEL_ID env:", os.getenv("MODEL_ID"))

factory = AgentRuntimeFactory()
runtime = factory.create("deep", "main-agent", config)

import asyncio
async def test():
    await runtime.initialize(config)
    print("Runtime initialized, agent type:", runtime.agent_type)
    
    # 检查 _agent 的 model
    agent = runtime._agent
    # deepagents 的 create_agent 返回 CompiledGraph
    # 内部 model 可能在 graph 的 config 中
    print("Agent class:", type(agent).__name__)
    
    # 直接测试 send_message
    dialog_id = await runtime.create_dialog("test")
    print("Dialog created:", dialog_id)
    
    events = []
    async for event in runtime.send_message(dialog_id, "hi", stream=True):
        print("Event:", event.type, event.data)
        events.append(event)
        if len(events) > 20:
            break
    
    print("Total events:", len(events))

asyncio.run(test())
