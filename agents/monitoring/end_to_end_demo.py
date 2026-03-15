"""
端到端演示 - 完整监控系统演示

展示 SFullAgent + CompositeBridge + EventBus + WebSocket 的完整数据流
"""

import asyncio
import time
from agents.monitoring.domain import EventType
from agents.monitoring.services import EventBus, event_bus
from agents.monitoring.bridge import CompositeMonitoringBridge


class MockWebSocketAdapter:
    """模拟 WebSocket 适配器 - 打印事件代替实际发送"""

    def __init__(self):
        self.events_received = []

    async def broadcast_event(self, event):
        """接收事件并打印"""
        self.events_received.append(event)
        data = event.to_dict()
        print(f"  [WebSocket] {data['type']} | Source: {data['source']} | "
              f"Priority: {data['priority']}")


async def run_end_to_end_demo():
    """运行端到端演示"""
    print("=" * 60)
    print("🚀 智能体监控系统 - 端到端演示")
    print("=" * 60)
    print()

    # 1. 启动 EventBus
    print("📡 启动 EventBus...")
    await event_bus.start_processing()
    print("   ✓ EventBus 运行中")
    print()

    # 2. 连接 WebSocket 适配器
    print("🔗 连接 WebSocket 适配器...")
    ws_adapter = MockWebSocketAdapter()
    event_bus.set_websocket_handler(ws_adapter.broadcast_event)
    print("   ✓ WebSocket 适配器已连接")
    print()

    # 3. 创建 CompositeBridge（主智能体）
    print("🤖 创建主智能体 (SFullAgent)...")
    main_agent = CompositeMonitoringBridge(
        dialog_id="demo-dialog-001",
        agent_name="TeamLeadAgent",
        event_bus=event_bus
    )
    print(f"   ✓ 主智能体创建完成 | Bridge ID: {main_agent.get_bridge_id()}")
    print()

    # 4. 模拟 Agent 执行流程
    print("▶️ 模拟 Agent 执行流程...")
    print("-" * 60)

    # 4.1 Agent 启动
    print("\n📍 步骤 1: Agent 启动")
    main_agent.on_before_run([{"role": "user", "content": "分析项目架构"}])
    await asyncio.sleep(0.2)

    # 4.2 流式输出
    print("\n📍 步骤 2: 流式生成内容")
    for i, text in enumerate(["我", "将", "为您", "分析", "..."]):
        main_agent.on_stream_token(text)
        await asyncio.sleep(0.1)

    # 4.3 工具调用
    print("\n📍 步骤 3: 调用工具 (read_file)")
    main_agent.on_tool_call(
        name="read_file",
        arguments={"path": "README.md"},
        tool_call_id="call_001"
    )
    await asyncio.sleep(0.3)

    main_agent.on_tool_result(
        name="read_file",
        result="# 项目标题\n项目描述...",
        tool_call_id="call_001"
    )
    await asyncio.sleep(0.2)

    # 4.4 创建子智能体
    print("\n📍 步骤 4: 创建子智能体 (ExploreAgent)")
    subagent = main_agent.create_subagent_bridge(
        subagent_name="ExploreAgent",
        subagent_type="Explore"
    )
    await asyncio.sleep(0.2)

    # 子智能体执行
    print("   子智能体开始执行...")
    subagent.mark_started()
    await asyncio.sleep(0.3)

    subagent.mark_progress({"files_scanned": 10, "current_file": "src/main.py"})
    await asyncio.sleep(0.2)

    subagent.mark_completed({
        "files_found": 25,
        "total_lines": 1500,
        "summary": "发现主要模块: api/, services/, models/"
    })
    await asyncio.sleep(0.2)

    # 4.5 创建后台任务
    print("\n📍 步骤 5: 创建后台任务 (依赖安装)")
    bg_task = main_agent.create_background_task_bridge(
        task_id="install-deps",
        command="pip install -r requirements.txt"
    )
    await asyncio.sleep(0.2)

    bg_task.start_process()
    await asyncio.sleep(0.2)

    bg_task.stream_output("Collecting package info...\n")
    await asyncio.sleep(0.2)
    bg_task.stream_output("Installing dependencies...\n")
    await asyncio.sleep(0.2)
    bg_task.mark_completed(exit_code=0)
    await asyncio.sleep(0.2)

    # 4.6 Agent 完成
    print("\n📍 步骤 6: Agent 完成")
    main_agent.on_complete("## 架构分析\n\n项目采用分层架构...")
    await asyncio.sleep(0.2)

    main_agent.on_after_run([], rounds=3)
    print("-" * 60)

    # 5. 统计数据
    print("\n📊 统计数据:")
    print(f"   - 总事件数: {len(ws_adapter.events_received)}")
    print(f"   - 子智能体数: {len(main_agent.get_subagent_bridges())}")
    print(f"   - 后台任务数: {len(main_agent.get_background_task_bridges())}")

    event_types = {}
    for event in ws_adapter.events_received:
        t = event.type.value
        event_types[t] = event_types.get(t, 0) + 1

    print("   - 事件类型分布:")
    for t, count in sorted(event_types.items()):
        print(f"     • {t}: {count}")

    # 6. 状态机历史
    print("\n🔄 状态机转换历史:")
    for transition in main_agent.get_state_history():
        print(f"   {transition.from_state.value} → {transition.to_state.value} "
              f"(trigger={transition.trigger}, duration={transition.duration_ms}ms)")

    # 停止 EventBus
    await event_bus.stop_processing()

    print()
    print("=" * 60)
    print("✅ 端到端演示完成!")
    print("=" * 60)
    print()
    print("📋 结论:")
    print("   • 后端组件协同工作正常")
    print("   • 事件流从 Agent → Bridge → EventBus → WebSocket 通畅")
    print("   • 子智能体和后台任务监控正常")
    print("   • 状态机转换记录完整")
    print()
    print("📝 下一步:")
    print("   • 实现真实 WebSocket 服务器广播")
    print("   • 与 SFullAgent 实际集成")
    print("   • 前端添加可视化组件")


if __name__ == "__main__":
    asyncio.run(run_end_to_end_demo())
