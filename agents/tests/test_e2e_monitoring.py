"""端到端测试 - 通过网页端测试 Agent 插件和监控。

测试流程:
1. 创建对话
2. 发送消息触发插件
3. 验证监控事件
"""

import asyncio
import json
import time
import websockets
import requests
from datetime import datetime


BASE_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001"
FRONTEND_URL = "http://localhost:3000"


class E2EMonitoringTest:
    """端到端监控测试。"""

    def __init__(self):
        self.dialog_id = None
        self.events = []
        self.ws = None

    def _api_post(self, endpoint: str, data: dict) -> dict:
        """发送 POST 请求到 API。"""
        response = requests.post(f"{BASE_URL}{endpoint}", json=data)
        return response.json()

    def _api_get(self, endpoint: str) -> dict:
        """发送 GET 请求到 API。"""
        response = requests.get(f"{BASE_URL}{endpoint}")
        return response.json()

    def create_dialog(self) -> str:
        """创建新对话。"""
        print("\n[步骤 1] 创建新对话...")
        result = self._api_post("/api/dialogs", {})
        if result.get("success"):
            self.dialog_id = result["data"]["id"]
            print(f"[✓] 对话创建成功: {self.dialog_id}")
            return self.dialog_id
        else:
            raise Exception(f"创建对话失败: {result}")

    def send_message(self, content: str) -> dict:
        """发送消息。"""
        print(f"\n[步骤 2] 发送消息: {content[:50]}...")
        result = self._api_post(
            f"/api/dialogs/{self.dialog_id}/messages",
            {"content": content}
        )
        if result.get("success"):
            print(f"[✓] 消息发送成功")
            return result
        else:
            raise Exception(f"发送消息失败: {result}")

    async def connect_websocket(self):
        """连接 WebSocket 接收监控事件。"""
        print(f"\n[步骤 3] 连接 WebSocket...")
        uri = f"{WS_URL}/ws/{self.dialog_id}"
        try:
            self.ws = await websockets.connect(uri)
            print(f"[✓] WebSocket 连接成功")
            return True
        except Exception as e:
            print(f"[!] WebSocket 连接失败: {e}")
            return False

    async def collect_events(self, duration: int = 30):
        """收集监控事件。"""
        print(f"\n[步骤 4] 收集监控事件 ({duration}秒)...")
        if not self.ws:
            print("[!] WebSocket 未连接，跳过事件收集")
            return

        start_time = time.time()
        try:
            while time.time() - start_time < duration:
                try:
                    msg = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                    data = json.loads(msg)
                    self.events.append(data)
                    event_type = data.get("event_type", "UNKNOWN")
                    print(f"  [事件] {event_type}")
                except asyncio.TimeoutError:
                    continue
        except Exception as e:
            print(f"[!] 事件收集出错: {e}")

        print(f"[✓] 共收集 {len(self.events)} 个事件")

    def check_events(self, expected_types: list) -> bool:
        """检查是否收到预期的事件类型。"""
        print(f"\n[步骤 5] 检查事件类型...")
        received_types = {e.get("event_type") for e in self.events}

        all_passed = True
        for event_type in expected_types:
            if event_type in received_types:
                print(f"  [✓] {event_type}")
            else:
                print(f"  [✗] {event_type} (未收到)")
                all_passed = False

        return all_passed

    async def run_test_scenario(self, name: str, message: str, expected_events: list, wait_time: int = 30):
        """运行一个测试场景。"""
        print("\n" + "="*60)
        print(f"测试场景: {name}")
        print("="*60)

        try:
            # 创建对话
            self.create_dialog()

            # 连接 WebSocket
            ws_connected = await self.connect_websocket()

            # 发送消息
            self.send_message(message)

            # 收集事件
            if ws_connected:
                await self.collect_events(duration=wait_time)

                # 检查事件
                events_ok = self.check_events(expected_events)
            else:
                print("[!] 跳过事件检查 (WebSocket 未连接)")
                events_ok = False

            # 清理
            if self.ws:
                await self.ws.close()

            return events_ok

        except Exception as e:
            print(f"\n[✗] 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_basic_conversation(self):
        """测试基础对话。"""
        return await self.run_test_scenario(
            name="基础对话",
            message="你好，请简单介绍一下自己",
            expected_events=["AGENT_STARTED", "AGENT_COMPLETED"],
            wait_time=10
        )

    async def test_todo_plugin(self):
        """测试 Todo 插件。"""
        return await self.run_test_scenario(
            name="Todo 插件",
            message="我有一个多步骤任务：1. 分析代码 2. 找出bug 3. 修复。请帮我跟踪",
            expected_events=["TODO_UPDATED", "TOOL_CALL"],
            wait_time=15
        )

    async def test_background_plugin(self):
        """测试 Background 插件。"""
        return await self.run_test_scenario(
            name="Background 插件",
            message="请帮我后台运行命令: echo 'Hello from background'，然后检查状态",
            expected_events=["BG_TASK_STARTED", "BG_TASK_COMPLETED"],
            wait_time=20
        )

    async def test_task_plugin(self):
        """测试 Task 插件。"""
        return await self.run_test_scenario(
            name="Task 插件",
            message="请创建一个持久化任务：标题\"测试任务\"，描述\"用于测试\"",
            expected_events=["TOOL_CALL"],
            wait_time=10
        )

    async def run_all_tests(self):
        """运行所有测试。"""
        print("="*60)
        print("Agent 插件与监控端到端测试")
        print("="*60)
        print(f"后端: {BASE_URL}")
        print(f"前端: {FRONTEND_URL}")
        print(f"WebSocket: {WS_URL}")

        # 检查服务是否可用
        try:
            response = requests.get(f"{BASE_URL}/api/dialogs", timeout=5)
            print(f"\n[✓] 后端服务正常")
        except Exception as e:
            print(f"\n[✗] 后端服务不可用: {e}")
            return False

        # 运行测试
        results = []

        results.append(("基础对话", await self.test_basic_conversation()))
        results.append(("Todo 插件", await self.test_todo_plugin()))
        results.append(("Task 插件", await self.test_task_plugin()))
        results.append(("Background 插件", await self.test_background_plugin()))

        # 汇总
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)

        passed = sum(1 for _, r in results if r)
        total = len(results)

        for name, result in results:
            status = "✓ 通过" if result else "✗ 失败"
            print(f"  [{status}] {name}")

        print(f"\n总计: {passed}/{total} 通过")

        return passed == total


async def main():
    """主函数。"""
    test = E2EMonitoringTest()
    success = await test.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
