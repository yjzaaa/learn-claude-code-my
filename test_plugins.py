#!/usr/bin/env python3
"""
测试 TeamLeadAgent 插件系统
"""

import asyncio
from agents.s09_agent_teams import TeamLeadAgent

async def test_agent_with_plugins():
    """测试带插件的 Agent"""
    print("=" * 60)
    print("Testing TeamLeadAgent with Plugins")
    print("=" * 60)

    # 创建 Agent（启用两个插件）
    agent = TeamLeadAgent(
        dialog_id="test-dialog-plugins",
        enable_skills=True,
        enable_compact=True,
    )

    print(f"[OK] Agent created with {len(agent.plugin_manager.plugins)} plugins")
    for plugin in agent.plugin_manager.plugins:
        print(f"  - {plugin.name}: {plugin.description}")

    print(f"[OK] Total tools: {len(agent.tools)}")
    print(f"  Tools: {[t.get('function', {}).get('name', t.get('name')) for t in agent.tools]}")

    # 测试系统提示词包含插件内容
    print(f"[OK] System prompt length: {len(agent.system)} chars")
    if "Available Skills" in agent.system:
        print("  - Skill descriptions included")
    if "Context Management" in agent.system:
        print("  - Context management instructions included")

    # 测试运行 Agent（模拟简单对话）
    print("\n" + "=" * 60)
    print("Running test conversation...")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "Hello, what skills do you have?"}
    ]

    # 注意：实际调用需要 API key，这里只测试到 on_before_run
    print("[OK] Testing plugin on_before_run...")
    agent.plugin_manager.on_before_run(messages)
    print(f"  Messages after on_before_run: {len(messages)}")

    print("[OK] All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_agent_with_plugins())
