"""
Test Agent Runtimes - Agent 运行时测试

测试 SimpleRuntime 和 DeepAgentRuntime 的核心功能。
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import BaseModel

# 添加项目根目录到路径
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from core.agent.runtime_factory import AgentRuntimeFactory
from core.models.config import EngineConfig
from core.runtime.interfaces import IAgentRuntime, AgentEvent
from core.session import DialogSessionManager


def _has_deepagents() -> bool:
    """检查 deepagents 是否可用"""
    try:
        import deepagents
        return True
    except ImportError:
        return False


class TestAgentRuntimeFactory:
    """测试 AgentRuntimeFactory"""

    def test_factory_initialization(self):
        """测试工厂初始化"""
        factory = AgentRuntimeFactory()
        assert factory is not None
        available_types = factory.available_types()
        assert "simple" in available_types
        assert "deep" in available_types

    def test_factory_create_simple(self):
        """测试创建 SimpleRuntime"""
        factory = AgentRuntimeFactory()
        config = EngineConfig.from_dict({"skills": {"skills_dir": "skills"}})

        runtime = factory.create("simple", "test-agent", config)

        assert runtime is not None
        assert runtime.runtime_id == "test-agent"
        assert runtime.agent_type == "simple"

    def test_factory_create_deep(self):
        """测试创建 DeepAgentRuntime"""
        # 检查 deepagents 是否可用
        try:
            import deepagents
            has_deepagents = True
        except ImportError:
            has_deepagents = False
            pytest.skip("deepagents not installed")

        factory = AgentRuntimeFactory()
        config = EngineConfig.from_dict({"skills": {"skills_dir": "skills"}})

        runtime = factory.create("deep", "test-agent", config)

        assert runtime is not None
        assert runtime.runtime_id == "test-agent"
        assert runtime.agent_type == "deep"

    def test_factory_create_unknown_type(self):
        """测试创建未知类型时抛出异常"""
        factory = AgentRuntimeFactory()
        config = EngineConfig.from_dict({})

        with pytest.raises(ValueError) as exc_info:
            factory.create("unknown", "test-agent", config)

        assert "Unknown agent type" in str(exc_info.value)
        assert "unknown" in str(exc_info.value)

    def test_factory_is_available(self):
        """测试类型可用性检查"""
        factory = AgentRuntimeFactory()

        assert factory.is_available("simple") is True
        assert factory.is_available("deep") is True
        assert factory.is_available("unknown") is False


class TestSimpleRuntime:
    """测试 SimpleRuntime"""

    @pytest.fixture
    async def runtime(self):
        """创建并初始化 SimpleRuntime"""
        factory = AgentRuntimeFactory()
        config = EngineConfig.from_dict({
            "skills": {"skills_dir": str(_PROJECT_ROOT / "skills")},
            "provider": {"model": "deepseek/deepseek-chat"},
        })

        rt = factory.create("simple", "test-simple-runtime", config)
        await rt.initialize(config)
        rt.set_session_manager(DialogSessionManager())
        yield rt
        await rt.shutdown()

    @pytest.mark.asyncio
    async def test_simple_runtime_lifecycle(self):
        """测试 SimpleRuntime 生命周期"""
        factory = AgentRuntimeFactory()
        config = EngineConfig.from_dict({
            "skills": {"skills_dir": str(_PROJECT_ROOT / "skills")},
        })

        runtime = factory.create("simple", "lifecycle-test", config)

        # 初始化
        await runtime.initialize(config)
        assert runtime.runtime_id == "lifecycle-test"
        assert runtime.agent_type == "simple"

        # 关闭
        await runtime.shutdown()

    @pytest.mark.asyncio
    async def test_create_dialog(self):
        """测试创建对话"""
        factory = AgentRuntimeFactory()
        config = EngineConfig.from_dict({"skills": {"skills_dir": "skills"}})

        runtime = factory.create("simple", "dialog-test", config)
        await runtime.initialize(config)
        runtime.set_session_manager(DialogSessionManager())

        try:
            dialog_id = await runtime.create_dialog("Hello", "Test Dialog")

            assert dialog_id is not None
            assert isinstance(dialog_id, str)
            assert len(dialog_id) > 0

            # 验证对话存在
            dialog = runtime.get_dialog(dialog_id)
            assert dialog is not None
            assert dialog.title == "Test Dialog"

        finally:
            await runtime.shutdown()

    @pytest.mark.asyncio
    async def test_list_dialogs(self):
        """测试列出所有对话"""
        factory = AgentRuntimeFactory()
        config = EngineConfig.from_dict({"skills": {"skills_dir": "skills"}})

        runtime = factory.create("simple", "list-test", config)
        await runtime.initialize(config)
        runtime.set_session_manager(DialogSessionManager())

        try:
            # 初始为空
            dialogs = runtime.list_dialogs()
            assert len(dialogs) == 0

            # 创建两个对话
            dialog1 = await runtime.create_dialog("Test 1", "Dialog 1")
            dialog2 = await runtime.create_dialog("Test 2", "Dialog 2")

            # 列出对话
            dialogs = runtime.list_dialogs()
            assert len(dialogs) == 2

            dialog_ids = [d.id for d in dialogs]
            assert dialog1 in dialog_ids
            assert dialog2 in dialog_ids

        finally:
            await runtime.shutdown()

    @pytest.mark.asyncio
    async def test_register_tool(self):
        """测试工具注册"""
        factory = AgentRuntimeFactory()
        config = EngineConfig.from_dict({"skills": {"skills_dir": "skills"}})

        runtime = factory.create("simple", "tool-test", config)
        await runtime.initialize(config)

        try:
            # 定义测试工具
            def test_tool(name: str) -> str:
                return f"Hello, {name}!"

            # 注册工具
            runtime.register_tool(
                name="test_tool",
                handler=test_tool,
                description="A test tool",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    }
                }
            )

            # 验证工具注册成功（通过检查 SimpleRuntime 的 _tools 属性）
            if hasattr(runtime, '_tools'):
                assert "test_tool" in runtime._tools

            # 注销工具
            runtime.unregister_tool("test_tool")

            if hasattr(runtime, '_tools'):
                assert "test_tool" not in runtime._tools

        finally:
            await runtime.shutdown()


class TestDeepAgentRuntime:
    """测试 DeepAgentRuntime（需要 deepagents）"""

    @pytest.fixture(scope="class")
    def has_deepagents(self):
        """检查 deepagents 是否可用"""
        try:
            import deepagents
            return True
        except ImportError:
            return False

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not _has_deepagents(),
        reason="deepagents not installed"
    )
    async def test_deep_runtime_lifecycle(self):
        """测试 DeepAgentRuntime 生命周期"""
        factory = AgentRuntimeFactory()
        config = EngineConfig.from_dict({
            "skills": {"skills_dir": str(_PROJECT_ROOT / "skills")},
        })

        runtime = factory.create("deep", "lifecycle-test", config)

        # 初始化
        await runtime.initialize(config)
        assert runtime.runtime_id == "lifecycle-test"
        assert runtime.agent_type == "deep"

        # 关闭
        await runtime.shutdown()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not _has_deepagents(),
        reason="deepagents not installed"
    )
    async def test_deep_create_dialog(self):
        """测试 DeepAgentRuntime 创建对话"""
        factory = AgentRuntimeFactory()
        config = EngineConfig.from_dict({
            "skills": {"skills_dir": str(_PROJECT_ROOT / "skills")},
        })

        runtime = factory.create("deep", "dialog-test", config)
        await runtime.initialize(config)
        runtime.set_session_manager(DialogSessionManager())

        try:
            dialog_id = await runtime.create_dialog("Hello", "Test Dialog")

            assert dialog_id is not None
            assert isinstance(dialog_id, str)

            # 验证对话存在
            dialog = runtime.get_dialog(dialog_id)
            assert dialog is not None
            assert dialog.title == "Test Dialog"

        finally:
            await runtime.shutdown()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not _has_deepagents(),
        reason="deepagents not installed"
    )
    async def test_deep_send_message(self):
        """测试 DeepAgentRuntime 发送消息并查看模型输出，原始事件写入 jsonl"""
        factory = AgentRuntimeFactory()
        config = EngineConfig.from_dict({
            "skills": {"skills_dir": str(_PROJECT_ROOT / "skills")},
        })

        runtime = factory.create("deep", "send-message-test", config)
        await runtime.initialize(config)
        runtime.set_session_manager(DialogSessionManager())

        try:
            dialog_id = await runtime.create_dialog("你好，请用一句话介绍自己", "Model Output Test")
            assert dialog_id is not None

            # 准备日志文件
            logs_dir = _PROJECT_ROOT / "logs" / "connectivity"
            logs_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            events_file = logs_dir / f"deep_runtime_send_message_{ts}.jsonl"

            print(f"\n[test_deep_send_message] 开始发送消息，日志: {events_file}\n")

            event_count = 0
            full_text = ""

            with open(events_file, "w", encoding="utf-8") as f:
                async for event in runtime.send_message(dialog_id, "How is the change of  HR allocation to 4130011 between  FY26 BGT and FY25 Actual?", stream=True):
                    event_count += 1
                    # 写入 jsonl
                    record = {
                        "index": event_count,
                        "timestamp": datetime.now().isoformat(),
                        "type": event.type,
                        "data": event.data,
                    }
                    f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

                    # 控制台打印
                    if event.type == "text_delta":
                        full_text += str(event.data)
                        print(str(event.data), end="", flush=True)
                    elif event.type == "tool_start":
                        print(f"\n[TOOL_START] {event.data}\n")
                    elif event.type == "tool_end":
                        print(f"\n[TOOL_END] {event.data}\n")
                    elif event.type == "complete":
                        print("\n[COMPLETE]")
                    elif event.type == "error":
                        print(f"\n[ERROR] {event.data}\n")

            print(f"\n[test_deep_send_message] 流结束")
            print(f"总事件数: {event_count}")
            print(f"完整回复: {full_text}")
            print(f"日志文件: {events_file}")

            # 基本断言：至少收到一些事件，且最终有文本或没有报错
            assert event_count > 0, "没有收到任何事件"

        finally:
            await runtime.shutdown()


def _has_deepagents() -> bool:
    """检查 deepagents 是否可用"""
    try:
        import deepagents
        return True
    except ImportError:
        return False


class TestRuntimeEventFlow:
    """测试运行时事件流"""

    @pytest.mark.asyncio
    async def test_event_types(self):
        """测试 AgentEvent 模型"""
        # 文本增量事件
        text_event = AgentEvent(type="text_delta", data="Hello")
        assert text_event.type == "text_delta"
        assert text_event.data == "Hello"

        # 工具开始事件
        tool_start = AgentEvent(
            type="tool_start",
            data={"name": "test_tool", "args": {"arg1": "value1"}}
        )
        assert tool_start.type == "tool_start"
        assert tool_start.data["name"] == "test_tool"

        # 完成事件
        complete_event = AgentEvent(type="complete", data="Final response")
        assert complete_event.type == "complete"

        # 错误事件
        error_event = AgentEvent(type="error", data="Something went wrong")
        assert error_event.type == "error"


class TestRuntimeConfiguration:
    """测试运行时配置"""

    def test_engine_config_from_dict(self):
        """测试 EngineConfig 从字典创建"""
        config = EngineConfig.from_dict({
            "skills": {"skills_dir": "/path/to/skills"},
            "provider": {"model": "claude-sonnet-4-6"},
            "dialog": {"max_history": 50},
        })

        assert config is not None
        # Windows 路径处理: 比较 Path 对象而不是字符串
        from pathlib import Path
        assert config.skills.skills_dir == Path("/path/to/skills")
        assert config.provider.model == "claude-sonnet-4-6"
        assert config.dialog.max_history == 50

    def test_engine_config_defaults(self):
        """测试 EngineConfig 默认值"""
        config = EngineConfig.from_dict({})

        assert config is not None
        assert config.dialog.max_history == 100
        assert config.provider.model == "deepseek/deepseek-chat"

    def test_engine_config_is_pydantic(self):
        """测试 EngineConfig 是 Pydantic BaseModel"""
        config = EngineConfig.from_dict({"skills": {"skills_dir": "skills"}})

        assert isinstance(config, BaseModel)
        assert hasattr(config, "model_dump")


class TestRuntimeIntegration:
    """集成测试 - 测试运行时完整流程"""

    @pytest.mark.asyncio
    async def test_simple_runtime_full_flow(self):
        """测试 SimpleRuntime 完整流程"""
        factory = AgentRuntimeFactory()
        config = EngineConfig.from_dict({
            "skills": {"skills_dir": str(_PROJECT_ROOT / "skills")},
        })

        runtime = factory.create("simple", "integration-test", config)

        try:
            # 1. 初始化
            await runtime.initialize(config)
            runtime.set_session_manager(DialogSessionManager())

            # 2. 创建对话
            dialog_id = await runtime.create_dialog("Hello", "Test Dialog")
            assert dialog_id is not None

            # 3. 列出对话
            dialogs = runtime.list_dialogs()
            assert len(dialogs) == 1

            # 4. 获取对话
            dialog = runtime.get_dialog(dialog_id)
            assert dialog is not None
            assert dialog.title == "Test Dialog"

            # 5. 注册工具
            def dummy_tool():
                return "dummy result"

            runtime.register_tool(
                name="dummy_tool",
                handler=dummy_tool,
                description="A dummy tool",
            )

            # 6. 停止
            await runtime.stop(dialog_id)

        finally:
            # 7. 关闭
            await runtime.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
