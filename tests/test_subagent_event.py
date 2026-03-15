#!/usr/bin/env python3
"""
测试子智能体监控事件是否正确发送和接收
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.monitoring.domain import MonitoringEvent, EventType, EventPriority
from agents.monitoring.services import event_bus

async def test_subagent_events():
    """测试子智能体事件"""
    print("=" * 60)
    print("测试子智能体监控事件")
    print("=" * 60)

    # 启动 event_bus 处理循环
    await event_bus.start_processing()
    print("\n[1] EventBus 处理循环已启动")

    # 检查 event_bus 状态
    stats = event_bus.get_stats()
    print(f"[2] EventBus 状态: {stats}")

    dialog_id = "test-dialog-123"

    # 发送 AGENT_STARTED 事件（模拟主 Agent 启动）
    print(f"\n[3] 发送 AGENT_STARTED 事件...")
    agent_started_event = MonitoringEvent(
        type=EventType.AGENT_STARTED,
        dialog_id=dialog_id,
        source="SFullAgent",
        context_id="test-context-1",
        priority=EventPriority.HIGH,
        payload={
            "agent_name": "SFullAgent",
            "bridge_id": "main-bridge-123"
        }
    )
    await event_bus.emit(agent_started_event)
    print(f"    [OK] AGENT_STARTED 事件已发送到队列")

    # 等待一下让事件被处理
    await asyncio.sleep(0.5)

    # 发送 SUBAGENT_STARTED 事件
    print(f"\n[4] 发送 SUBAGENT_STARTED 事件...")
    subagent_event = MonitoringEvent(
        type=EventType.SUBAGENT_STARTED,
        dialog_id=dialog_id,
        source="Subagent:Explore:CodeAnalyzer",
        context_id="test-context-2",
        priority=EventPriority.HIGH,
        payload={
            "subagent_name": "CodeAnalyzer",
            "subagent_type": "Explore",
            "task_preview": "分析项目结构"
        }
    )
    await event_bus.emit(subagent_event)
    print(f"    [OK] SUBAGENT_STARTED 事件已发送到队列")

    # 等待一下让事件被处理
    await asyncio.sleep(0.5)

    # 发送 SUBAGENT_COMPLETED 事件
    print(f"\n[5] 发送 SUBAGENT_COMPLETED 事件...")
    completed_event = MonitoringEvent(
        type=EventType.SUBAGENT_COMPLETED,
        dialog_id=dialog_id,
        source="Subagent:Explore:CodeAnalyzer",
        context_id="test-context-3",
        priority=EventPriority.HIGH,
        payload={
            "subagent_name": "CodeAnalyzer",
            "subagent_type": "Explore",
            "result_preview": "找到 5 个 Python 文件"
        }
    )
    await event_bus.emit(completed_event)
    print(f"    [OK] SUBAGENT_COMPLETED 事件已发送到队列")

    # 等待事件处理
    print(f"\n[6] 等待事件处理...")
    await asyncio.sleep(2)

    # 检查最终状态
    stats = event_bus.get_stats()
    print(f"\n[7] 最终 EventBus 状态: {stats}")

    # 停止处理
    await event_bus.stop_processing()
    print("\n[8] EventBus 处理循环已停止")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n请检查:")
    print("1. 后端日志中是否有 '[EventBus] Dispatching:' 的日志")
    print("2. 如果有 WebSocket 客户端连接，是否收到 monitor:subagent:started 事件")

if __name__ == "__main__":
    asyncio.run(test_subagent_events())
