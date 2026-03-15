"""
测试异步后台子任务监控

流程:
1. 创建对话
2. 发送消息触发需要后台执行的任务（如文件操作、长时间计算）
3. 验证监控页面显示后台任务状态
4. 检查 BG_TASK_* 事件是否正确发送
"""

import asyncio
import json
import requests
import websockets
from datetime import datetime

BACKEND_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001/ws"


async def test_background_task_monitoring():
    """测试后台任务监控"""

    print("=" * 70)
    print("Background Task Monitoring Test")
    print("=" * 70)

    # 1. 创建对话
    print("\n[1] Creating dialog...")
    resp = requests.post(f"{BACKEND_URL}/api/dialogs", json={})
    dialog_data = resp.json()

    if 'data' not in dialog_data or 'id' not in dialog_data['data']:
        print(f"   Failed: {dialog_data}")
        return

    dialog_id = dialog_data['data']['id']
    print(f"   Dialog ID: {dialog_id}")

    # 2. 连接 WebSocket 监听事件
    print("\n[2] Connecting WebSocket...")
    client_id = f"bg_task_test_{datetime.now().strftime('%H%M%S')}"
    ws_uri = f"{WS_URL}/{client_id}"

    async with websockets.connect(ws_uri) as ws:
        # 订阅对话
        await ws.send(json.dumps({
            "type": "subscribe",
            "dialog_id": dialog_id
        }))
        print(f"   Subscribed to dialog {dialog_id}")

        # 3. 发送触发后台任务的消息
        print("\n[3] Sending message to trigger background task...")

        # 提示词要求 Agent 执行需要后台处理的操作
        prompt = """Please help me with the following tasks:
1. List all files in the current directory
2. Check the git status if it's a git repo
3. Run a simple Python script that takes a few seconds

Use the available tools to execute these commands in the background."""

        msg_resp = requests.post(
            f"{BACKEND_URL}/api/dialogs/{dialog_id}/messages",
            json={"content": prompt, "role": "user"}
        )
        print(f"   Message sent: {msg_resp.status_code}")

        # 4. 监听事件
        print("\n[4] Listening for events (30 seconds)...")
        print("-" * 70)

        bg_task_events = []
        all_events = []

        try:
            for i in range(60):  # 60 * 0.5s = 30s
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    data = json.loads(msg)
                    event_type = data.get("type", "unknown")
                    all_events.append(event_type)

                    # 记录后台任务相关事件
                    if "bg_task" in event_type or "BG_TASK" in event_type:
                        bg_task_events.append(data)
                        print(f"[BG_TASK] {event_type}")
                        if "payload" in data:
                            print(f"         Payload: {json.dumps(data['payload'], indent=2)[:200]}")

                    # 监控状态转换
                    elif "state" in event_type:
                        print(f"[STATE] {event_type}")

                    # 子智能体事件
                    elif "subagent" in event_type:
                        print(f"[SUBAGENT] {event_type}")

                except asyncio.TimeoutError:
                    pass

                if i % 10 == 0:
                    print(f"   Progress: {i//2}s... (events: {len(all_events)})")

        except KeyboardInterrupt:
            print("\n   Stopped by user")

        print("-" * 70)

        # 5. 分析报告
        print("\n[5] Test Report:")
        print(f"   Total events received: {len(all_events)}")
        print(f"   Background task events: {len(bg_task_events)}")

        if bg_task_events:
            print("\n   Background Task Event Types:")
            for event in bg_task_events:
                print(f"      - {event.get('type')}")

            print("\n   Background Task Details:")
            for event in bg_task_events[:5]:  # 显示前5个
                payload = event.get("payload", {})
                print(f"\n      Event: {event.get('type')}")
                print(f"      Time: {event.get('timestamp')}")
                if "task_id" in payload:
                    print(f"      Task ID: {payload['task_id']}")
                if "command" in payload:
                    print(f"      Command: {payload['command'][:100]}")
                if "status" in payload:
                    print(f"      Status: {payload['status']}")
        else:
            print("\n   No background task events captured!")
            print("   This may mean:")
            print("   - The agent didn't use background task tools")
            print("   - BackgroundTaskBridge is not properly integrated")
            print("   - Events are not being sent to WebSocket")

        # 6. 获取对话最终状态
        print("\n[6] Checking dialog final state...")
        dialog_resp = requests.get(f"{BACKEND_URL}/api/dialogs/{dialog_id}")
        if dialog_resp.status_code == 200:
            dialog_info = dialog_resp.json()
            print(f"   Dialog status: {dialog_info.get('data', {}).get('status', 'unknown')}")
            messages = dialog_info.get('data', {}).get('messages', [])
            print(f"   Message count: {len(messages)}")

        # 7. 清理
        print("\n[7] Cleaning up...")
        requests.delete(f"{BACKEND_URL}/api/dialogs/{dialog_id}")
        print("   Done")

    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(test_background_task_monitoring())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
