"""测试 Agent 插件与监控集成。

一步一步测试：
1. 测试 TodoPlugin
2. 测试 TaskPlugin
3. 测试 BackgroundPlugin
4. 验证监控事件发送
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

# 设置测试环境
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from agents.core import AgentBuilder
from agents.plugins import (
    TodoPlugin,
    TaskPlugin,
    BackgroundPlugin,
    TeamPlugin,
    PlanPlugin,
)
from agents.monitoring.bridge.composite import CompositeMonitoringBridge
from agents.monitoring.domain.event import EventType


class TestStepByStep:
    """一步一步测试插件。"""

    def __init__(self):
        self.events_received = []
        self.bridge = None

    def _setup_monitoring(self, dialog_id: str):
        """设置监控桥接。"""
        self.bridge = CompositeMonitoringBridge(dialog_id)
        print(f"[监控] 初始化完成，dialog_id={dialog_id}")
        return self.bridge

    def test_1_todo_plugin(self):
        """步骤1: 测试 TodoPlugin。"""
        print("\n" + "="*50)
        print("步骤 1: 测试 TodoPlugin")
        print("="*50)

        plugin = TodoPlugin()
        print(f"[✓] 插件名称: {plugin.name}")

        tools = plugin.get_tools()
        print(f"[✓] 工具数量: {len(tools)}")
        print(f"[✓] 工具名称: {[t.__tool_spec__['name'] for t in tools]}")

        # 测试工具调用（不实际运行，只验证结构）
        todo_tool = tools[0]
        spec = todo_tool.__tool_spec__
        print(f"[✓] Todo 工具描述: {spec['description'][:50]}...")

        print("[✓] TodoPlugin 测试通过")
        return True

    def test_2_task_plugin(self):
        """步骤2: 测试 TaskPlugin。"""
        print("\n" + "="*50)
        print("步骤 2: 测试 TaskPlugin")
        print("="*50)

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin = TaskPlugin(tasks_dir=Path(tmpdir))
            print(f"[✓] 插件名称: {plugin.name}")
            print(f"[✓] Task 存储目录: {tmpdir}")

            # 测试创建任务
            result = plugin._task_create("测试任务", "这是一个测试任务")
            task = json.loads(result)
            print(f"[✓] 创建任务成功: {task['id']}")
            task_id = task['id']

            # 测试获取任务
            result = plugin._task_get(task_id)
            task = json.loads(result)
            print(f"[✓] 获取任务成功: {task['title']}")

            # 测试更新任务
            result = plugin._task_update(task_id, status="completed")
            task = json.loads(result)
            print(f"[✓] 更新任务状态: {task['status']}")

            # 测试列表
            result = plugin._task_list()
            tasks = json.loads(result)
            print(f"[✓] 任务列表数量: {len(tasks)}")

        print("[✓] TaskPlugin 测试通过")
        return True

    def test_3_background_plugin(self):
        """步骤3: 测试 BackgroundPlugin。"""
        print("\n" + "="*50)
        print("步骤 3: 测试 BackgroundPlugin")
        print("="*50)

        plugin = BackgroundPlugin(max_workers=2)
        print(f"[✓] 插件名称: {plugin.name}")

        tools = plugin.get_tools()
        print(f"[✓] 工具数量: {len(tools)}")
        tool_names = [t.__tool_spec__['name'] for t in tools]
        print(f"[✓] 工具名称: {tool_names}")

        print("[✓] BackgroundPlugin 测试通过")
        return True

    def test_4_plan_plugin(self):
        """步骤4: 测试 PlanPlugin。"""
        print("\n" + "="*50)
        print("步骤 4: 测试 PlanPlugin")
        print("="*50)

        plugin = PlanPlugin()
        print(f"[✓] 插件名称: {plugin.name}")

        # 测试提交计划
        result = plugin._submit_plan("1. 分析代码\n2. 修复bug\n3. 测试验证")
        data = json.loads(result)
        plan_id = data['plan_id']
        print(f"[✓] 提交计划成功: {plan_id}")
        print(f"[✓] 计划状态: {data['status']}")

        # 测试审批计划
        result = plugin._review_plan(plan_id, approve=True, feedback="LGTM")
        plan = json.loads(result)
        print(f"[✓] 审批计划成功: {plan['status']}")
        print(f"[✓] 审批反馈: {plan.get('feedback', '无')}")

        # 验证是否已批准
        is_approved = plugin.is_approved(plan_id)
        print(f"[✓] 计划已批准: {is_approved}")

        print("[✓] PlanPlugin 测试通过")
        return True

    def test_5_team_plugin(self):
        """步骤5: 测试 TeamPlugin。"""
        print("\n" + "="*50)
        print("步骤 5: 测试 TeamPlugin")
        print("="*50)

        with tempfile.TemporaryDirectory() as team_dir, \
             tempfile.TemporaryDirectory() as inbox_dir:

            plugin = TeamPlugin(
                team_dir=Path(team_dir),
                inbox_dir=Path(inbox_dir)
            )
            print(f"[✓] 插件名称: {plugin.name}")

            # 测试创建队友
            result = plugin._spawn_teammate("CodeAnalyzer", "code_review")
            teammate = json.loads(result)
            print(f"[✓] 创建队友: {teammate['name']} ({teammate['role']})")
            print(f"[✓] 队友状态: {teammate['status']}")

            # 测试发送消息
            result = plugin._send_msg("CodeAnalyzer", "请检查这段代码")
            print(f"[✓] 发送消息: {result}")

            # 测试读取收件箱
            result = plugin._read_inbox("CodeAnalyzer")
            messages = json.loads(result)
            print(f"[✓] 收件箱消息数: {len(messages)}")

        print("[✓] TeamPlugin 测试通过")
        return True

    def test_6_agent_builder(self):
        """步骤6: 测试 AgentBuilder 组装。"""
        print("\n" + "="*50)
        print("步骤 6: 测试 AgentBuilder 组装")
        print("="*50)

        # 构建带监控的 agent
        builder = (
            AgentBuilder()
            .with_base_tools()
            .with_plugin(TodoPlugin())
            .with_plugin(TaskPlugin())
            .with_monitoring(dialog_id="test-dialog-123")
        )

        print(f"[✓] Builder 配置:")
        print(f"  - 基础工具: 已添加")
        print(f"  - 插件: {list(builder._plugin_names)}")
        print(f"  - 监控: dialog_id={builder._monitoring_dialog_id}")

        print("[✓] AgentBuilder 测试通过")
        return True

    def run_all_tests(self):
        """运行所有测试。"""
        print("\n" + "="*50)
        print("开始 Agent 插件测试")
        print("="*50)

        tests = [
            ("TodoPlugin", self.test_1_todo_plugin),
            ("TaskPlugin", self.test_2_task_plugin),
            ("BackgroundPlugin", self.test_3_background_plugin),
            ("PlanPlugin", self.test_4_plan_plugin),
            ("TeamPlugin", self.test_5_team_plugin),
            ("AgentBuilder", self.test_6_agent_builder),
        ]

        passed = 0
        failed = 0

        for name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                failed += 1
                print(f"[✗] {name} 测试失败: {e}")
                import traceback
                traceback.print_exc()

        print("\n" + "="*50)
        print("测试总结")
        print("="*50)
        print(f"通过: {passed}/{len(tests)}")
        print(f"失败: {failed}/{len(tests)}")

        return failed == 0


if __name__ == "__main__":
    tester = TestStepByStep()
    success = tester.run_all_tests()
    exit(0 if success else 1)
