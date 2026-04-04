"""
Test DeepAgentRuntime SessionManager Integration
测试 DeepAgentRuntime 与 SessionManager 的集成

验证 Runtime 是否正确与 SessionManager 交互进行对话历史管理。
"""

import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 添加项目根目录到路径
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from core.agent.runtimes.deep_runtime import DeepAgentRuntime


def _has_deepagents() -> bool:
    """检查 deepagents 是否可用"""
    try:
        import deepagents
        return True
    except ImportError:
        return False


class SerializableMagicMock(MagicMock):
    """可 JSON 序列化的 MagicMock"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mock_content = ""
        self._mock_additional_kwargs = {}
    
    @property
    def content(self):
        return self._mock_content
    
    @content.setter
    def content(self, value):
        self._mock_content = value
    
    @property
    def additional_kwargs(self):
        return self._mock_additional_kwargs
    
    @additional_kwargs.setter
    def additional_kwargs(self, value):
        self._mock_additional_kwargs = value


class TestDeepRuntimeSessionIntegration:
    """DeepAgentRuntime SessionManager 集成测试"""

    @pytest.fixture
    def mock_session_manager(self):
        """创建 Mock SessionManager"""
        mgr = MagicMock()
        
        # 模拟异步方法
        mgr.get_session = AsyncMock(return_value=None)
        mgr.create_session = AsyncMock()
        mgr.add_user_message = AsyncMock()
        mgr.get_messages = AsyncMock(return_value=[])
        mgr.start_ai_response = AsyncMock()
        mgr.emit_delta = AsyncMock()
        mgr.emit_reasoning_delta = AsyncMock()
        mgr.complete_ai_response = AsyncMock()
        mgr.add_tool_result = AsyncMock()
        
        return mgr

    @pytest.fixture
    def runtime_with_session_mgr(self, mock_session_manager):
        """创建带有 Mock SessionManager 的 Runtime"""
        runtime = DeepAgentRuntime("test-agent")
        runtime._agent = MagicMock()
        runtime._msg_logger = MagicMock()
        runtime._update_logger = MagicMock()
        runtime._value_logger = MagicMock()
        runtime.set_session_manager(mock_session_manager)
        return runtime, mock_session_manager

    @pytest.mark.asyncio
    async def test_send_message_creates_session_if_not_exists(self, runtime_with_session_mgr):
        """测试当会话不存在时自动创建"""
        runtime, mock_mgr = runtime_with_session_mgr
        
        # 模拟 agent.astream 返回空
        async def mock_astream(*args, **kwargs):
            if False:
                yield None
        
        runtime._agent.astream = mock_astream
        
        # 执行
        dialog_id = "new-dialog-123"
        async for _ in runtime.send_message(dialog_id, "Hello"):
            pass
        
        # 验证：创建了会话
        mock_mgr.create_session.assert_called_once_with(dialog_id, title="Hello")

    @pytest.mark.asyncio
    async def test_send_message_adds_user_message(self, runtime_with_session_mgr):
        """测试用户消息被添加到 SessionManager"""
        runtime, mock_mgr = runtime_with_session_mgr
        
        async def mock_astream(*args, **kwargs):
            if False:
                yield None
        
        runtime._agent.astream = mock_astream
        
        dialog_id = "dlg-001"
        message = "测试消息"
        
        async for _ in runtime.send_message(dialog_id, message):
            pass
        
        # 验证：添加了用户消息
        mock_mgr.add_user_message.assert_called_once_with(dialog_id, message)

    @pytest.mark.asyncio
    async def test_send_message_gets_history(self, runtime_with_session_mgr):
        """测试从 SessionManager 获取对话历史"""
        runtime, mock_mgr = runtime_with_session_mgr
        
        # 设置历史消息
        from langchain_core.messages import HumanMessage, AIMessage
        history = [
            HumanMessage(content="你好"),
            AIMessage(content="你好！有什么可以帮你的？"),
        ]
        mock_mgr.get_messages = AsyncMock(return_value=history)
        
        captured_input = None
        async def capture_astream(input_data, config, **kwargs):
            nonlocal captured_input
            captured_input = input_data
            if False:
                yield None
        
        runtime._agent.astream = capture_astream
        
        async for _ in runtime.send_message("dlg-002", "今天天气怎么样？"):
            pass
        
        # 验证：获取了历史
        mock_mgr.get_messages.assert_called_once_with("dlg-002")
        # 验证：发送给 agent 的消息包含历史
        assert captured_input is not None
        assert "messages" in captured_input
        # 消息列表包含历史消息（可能有重复，因为 add_user_message 已经添加了新消息）
        assert len(captured_input["messages"]) >= 2  # 至少2条历史消息

    @pytest.mark.asyncio
    async def test_send_message_starts_ai_response(self, runtime_with_session_mgr):
        """测试标记 AI 响应开始"""
        runtime, mock_mgr = runtime_with_session_mgr
        
        async def mock_astream(*args, **kwargs):
            if False:
                yield None
        
        runtime._agent.astream = mock_astream
        
        dialog_id = "dlg-003"
        message_id = "custom-msg-id"
        
        async for _ in runtime.send_message(dialog_id, "Hello", message_id=message_id):
            pass
        
        # 验证：标记了 AI 响应开始
        mock_mgr.start_ai_response.assert_called_once_with(dialog_id, message_id)

    @pytest.mark.asyncio
    async def test_send_message_emits_deltas(self, runtime_with_session_mgr):
        """测试流式增量被转发到 SessionManager"""
        runtime, mock_mgr = runtime_with_session_mgr
        
        # 模拟流式输出 - 使用简单元组
        async def mock_astream(*args, **kwargs):
            # 创建简单的消息对象而不是 MagicMock
            class SimpleChunk:
                def __init__(self, content, reasoning=""):
                    self.content = content
                    self.additional_kwargs = {"reasoning_content": reasoning} if reasoning else {}
            
            chunk1 = SimpleChunk("Hello")
            chunk2 = SimpleChunk(" World")
            
            yield ("messages", (chunk1, {}))
            yield ("messages", (chunk2, {}))
        
        runtime._agent.astream = mock_astream
        
        dialog_id = "dlg-004"
        
        async for _ in runtime.send_message(dialog_id, "Hi"):
            pass
        
        # 验证：转发了 delta（检查调用次数和参数内容）
        assert mock_mgr.emit_delta.call_count == 2
        # 检查第一个调用参数
        call1 = mock_mgr.emit_delta.call_args_list[0]
        assert call1[0][0] == dialog_id  # dialog_id
        assert call1[0][1] == "Hello"    # delta

    @pytest.mark.asyncio
    async def test_send_message_completes_ai_response(self, runtime_with_session_mgr):
        """测试 AI 响应完成后保存到 SessionManager"""
        runtime, mock_mgr = runtime_with_session_mgr
        
        class SimpleChunk:
            def __init__(self, content):
                self.content = content
                self.additional_kwargs = {}
        
        async def mock_astream(*args, **kwargs):
            chunk = SimpleChunk("完整响应")
            yield ("messages", (chunk, {}))
        
        runtime._agent.astream = mock_astream
        
        dialog_id = "dlg-005"
        message_id = "msg-005"
        
        async for _ in runtime.send_message(dialog_id, "Hello", message_id=message_id):
            pass
        
        # 验证：完成了 AI 响应
        mock_mgr.complete_ai_response.assert_called_once()
        call_args = mock_mgr.complete_ai_response.call_args
        assert call_args[0][0] == dialog_id
        assert call_args[0][1] == message_id
        assert call_args[0][2] == "完整响应"

    @pytest.mark.asyncio
    async def test_send_message_with_reasoning(self, runtime_with_session_mgr):
        """测试推理内容被转发"""
        runtime, mock_mgr = runtime_with_session_mgr
        
        class SimpleChunk:
            def __init__(self, content, reasoning=""):
                self.content = content
                self.additional_kwargs = {"reasoning_content": reasoning} if reasoning else {}
        
        async def mock_astream(*args, **kwargs):
            chunk = SimpleChunk("答案", "推理过程")
            yield ("messages", (chunk, {}))
        
        runtime._agent.astream = mock_astream
        
        async for _ in runtime.send_message("dlg-006", "问题"):
            pass
        
        # 验证：转发了推理内容
        mock_mgr.emit_reasoning_delta.assert_called_once()
        call_args = mock_mgr.emit_reasoning_delta.call_args
        assert call_args[0][0] == "dlg-006"
        assert call_args[0][1] == "推理过程"

    @pytest.mark.asyncio
    async def test_send_message_saves_reasoning_in_metadata(self, runtime_with_session_mgr):
        """测试推理内容被保存到元数据"""
        runtime, mock_mgr = runtime_with_session_mgr
        
        class SimpleChunk:
            def __init__(self, content, reasoning=""):
                self.content = content
                self.additional_kwargs = {"reasoning_content": reasoning} if reasoning else {}
        
        async def mock_astream(*args, **kwargs):
            chunk = SimpleChunk("答案", "推理过程")
            yield ("messages", (chunk, {}))
        
        runtime._agent.astream = mock_astream
        
        async for _ in runtime.send_message("dlg-007", "问题"):
            pass
        
        # 验证：推理内容在元数据中
        call_args = mock_mgr.complete_ai_response.call_args
        assert call_args[1]["metadata"]["reasoning_content"] == "推理过程"

    @pytest.mark.asyncio
    async def test_send_message_without_session_manager(self):
        """测试没有 SessionManager 时的回退行为"""
        runtime = DeepAgentRuntime("test-agent")
        runtime._agent = MagicMock()
        runtime._msg_logger = MagicMock()
        runtime._update_logger = MagicMock()
        runtime._value_logger = MagicMock()
        # 不设置 session_manager
        
        async def mock_astream(*args, **kwargs):
            if False:
                yield None
        
        runtime._agent.astream = mock_astream
        
        # 执行不应抛出异常
        events = []
        async for event in runtime.send_message("dlg-008", "Hello"):
            events.append(event)
        
        # 验证：正常完成
        assert isinstance(events, list)


class TestDeepRuntimeSessionIntegrationWithRealSessionManager:
    """使用真实 SessionManager 的集成测试"""

    @pytest.fixture
    async def real_session_manager(self):
        """创建真实的 SessionManager"""
        from core.session.manager import DialogSessionManager
        from core.session.exceptions import InvalidTransitionError
        
        mgr = DialogSessionManager(max_sessions=10)
        yield mgr
        # 清理所有会话 - 处理状态转换限制
        for dialog_id in list(mgr._sessions.keys()):
            try:
                session = mgr._sessions.get(dialog_id)
                if session and session.status.value in ["streaming", "active"]:
                    # 先转换到 completed
                    session.status = mgr._sessions[dialog_id].status.__class__("completed")
                await mgr.close_session(dialog_id)
            except InvalidTransitionError:
                # 如果无法关闭，直接删除
                mgr._sessions.pop(dialog_id, None)
                mgr._locks.pop(dialog_id, None)

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, real_session_manager):
        """测试多轮对话历史正确累积"""
        runtime = DeepAgentRuntime("test-agent")
        runtime._agent = MagicMock()
        runtime._msg_logger = MagicMock()
        runtime._update_logger = MagicMock()
        runtime._value_logger = MagicMock()
        runtime.set_session_manager(real_session_manager)
        
        class SimpleChunk:
            def __init__(self, content):
                self.content = content
                self.additional_kwargs = {}
        
        async def mock_astream(*args, **kwargs):
            messages = args[0].get("messages", [])
            # 模拟 AI 回复最后一条消息
            last_msg = messages[-1].get("content", "") if messages else ""
            chunk = SimpleChunk(f"回复: {last_msg}")
            yield ("messages", (chunk, {}))
        
        runtime._agent.astream = mock_astream
        
        dialog_id = "multi-turn-dlg"
        
        # 第一轮
        async for _ in runtime.send_message(dialog_id, "你好"):
            pass
        
        messages = await real_session_manager.get_messages(dialog_id)
        assert len(messages) == 2  # 用户 + AI
        
        # 第二轮
        async for _ in runtime.send_message(dialog_id, "今天怎么样？"):
            pass
        
        messages = await real_session_manager.get_messages(dialog_id)
        assert len(messages) == 4  # 用户 + AI + 用户 + AI

    @pytest.mark.asyncio
    async def test_session_status_transitions(self, real_session_manager):
        """测试会话状态正确转换"""
        from core.session.models import SessionStatus
        
        runtime = DeepAgentRuntime("test-agent")
        runtime._agent = MagicMock()
        runtime._msg_logger = MagicMock()
        runtime._update_logger = MagicMock()
        runtime._value_logger = MagicMock()
        runtime.set_session_manager(real_session_manager)
        
        class SimpleChunk:
            def __init__(self, content):
                self.content = content
                self.additional_kwargs = {}
        
        async def mock_astream(*args, **kwargs):
            chunk = SimpleChunk("Hi")
            yield ("messages", (chunk, {}))
        
        runtime._agent.astream = mock_astream
        
        dialog_id = "status-test-dlg"
        
        # 发送消息前创建会话
        await real_session_manager.create_session(dialog_id)
        assert real_session_manager._sessions[dialog_id].status == SessionStatus.ACTIVE
        
        # 发送消息
        async for _ in runtime.send_message(dialog_id, "Hello"):
            pass
        
        # 完成后应为 COMPLETED 状态
        assert real_session_manager._sessions[dialog_id].status == SessionStatus.COMPLETED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
