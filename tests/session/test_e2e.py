"""
端到端测试 - 完整流程测试

测试 DialogSessionManager 与 Runtime 的集成。
"""

import asyncio

import pytest

from backend.domain.models.config import EngineConfig
from backend.domain.models.dialog import DialogSessionManager, SessionStatus
from backend.domain.models.dialog.session import SessionEvent
from backend.infrastructure.runtime.simple import SimpleRuntime


@pytest.fixture
async def session_manager():
    """创建测试用的 SessionManager"""
    mgr = DialogSessionManager(max_sessions=10, session_ttl_seconds=300)
    yield mgr
    # 清理所有会话
    for dialog_id in list(mgr._sessions.keys()):
        await mgr.close_session(dialog_id)


@pytest.fixture
async def runtime(session_manager):
    """创建测试用的 Runtime"""
    rt = SimpleRuntime("test-agent")
    rt.set_session_manager(session_manager)

    config = EngineConfig.from_dict({
        "skills": {"skills_dir": "./skills"},
        "provider": {
            "model": "claude-sonnet-4-6",
            "api_key": "test-key",
        },
        "system": "You are a test assistant.",
    })
    await rt.initialize(config)
    yield rt
    await rt.shutdown()


@pytest.mark.asyncio
async def test_full_conversation_flow(session_manager, runtime):
    """测试完整对话流程"""
    dialog_id = "test_dialog_001"

    # 1. 创建对话
    await runtime.create_dialog("Hello", title="Test Dialog")

    # 2. 验证会话状态
    session = await session_manager.get_session(dialog_id)
    assert session is not None
    assert session.status == SessionStatus.ACTIVE

    # 3. 发送消息并接收流式响应
    events: list[SessionEvent] = []

    async def event_handler(event: SessionEvent):
        events.append(event)

    session_manager.set_event_handler(event_handler)

    # 由于我们没有真正的 LLM provider，这里只测试消息添加
    await session_manager.add_user_message(dialog_id, "What is AI?")

    session = await session_manager.get_session(dialog_id)
    assert session.message_count == 1
    assert session.status == SessionStatus.ACTIVE

    # 4. 模拟 AI 响应流程
    await session_manager.start_ai_response(dialog_id, "msg_001")

    session = await session_manager.get_session(dialog_id)
    assert session.status == SessionStatus.STREAMING

    # 5. 转发 delta（不存储）
    await session_manager.emit_delta(dialog_id, "AI ")
    await session_manager.emit_delta(dialog_id, "is ")
    await session_manager.emit_delta(dialog_id, "artificial intelligence.")

    # 6. 完成响应
    await session_manager.complete_ai_response(
        dialog_id, "msg_001", "AI is artificial intelligence."
    )

    session = await session_manager.get_session(dialog_id)
    assert session.status == SessionStatus.COMPLETED
    assert session.message_count == 2  # user + ai

    # 7. 验证事件
    assert len(events) > 0
    event_types = [e.type for e in events]
    assert "delta" in event_types
    assert "completed" in event_types


@pytest.mark.asyncio
async def test_multiple_conversations(session_manager):
    """测试多会话并发"""
    dialog_ids = ["dlg_001", "dlg_002", "dlg_003"]

    # 创建多个会话
    for dlg_id in dialog_ids:
        await session_manager.create_session(dlg_id, f"Dialog {dlg_id}")

    # 并发添加消息
    async def add_messages(dlg_id: str):
        await session_manager.add_user_message(dlg_id, f"Hello from {dlg_id}")
        await session_manager.start_ai_response(dlg_id, f"msg_{dlg_id}")
        await session_manager.complete_ai_response(
            dlg_id, f"msg_{dlg_id}", f"Response for {dlg_id}"
        )

    # 并发执行
    await asyncio.gather(*[add_messages(dlg_id) for dlg_id in dialog_ids])

    # 验证所有会话
    for dlg_id in dialog_ids:
        session = await session_manager.get_session(dlg_id)
        assert session is not None
        assert session.message_count == 2  # user + ai
        assert session.status == SessionStatus.COMPLETED


@pytest.mark.asyncio
async def test_conversation_with_tool_calls(session_manager):
    """测试带工具调用的对话"""
    dialog_id = "tool_test_001"

    # 创建会话
    await session_manager.create_session(dialog_id)

    # 添加用户消息
    await session_manager.add_user_message(dialog_id, "Run a query")

    # 模拟工具调用
    await session_manager.add_tool_result(
        dialog_id,
        tool_call_id="call_001",
        content='{"rows": 5, "data": [...]}',
        metadata={"tool_name": "run_sql_query"}
    )

    # 验证消息
    messages = await session_manager.get_messages(dialog_id)
    assert len(messages) == 2  # user + tool
    assert messages[1].type == "tool"


@pytest.mark.asyncio
async def test_session_cleanup(session_manager):
    """测试会话清理"""
    # 创建会话
    await session_manager.create_session("cleanup_test_001")

    # 手动设置最后活动时间为很久以前
    session = await session_manager.get_session("cleanup_test_001")
    from datetime import datetime, timedelta
    session.last_activity_at = datetime.now() - timedelta(seconds=4000)

    # 执行清理
    expired = await session_manager.cleanup_expired()

    assert "cleanup_test_001" in expired

    # 验证已关闭
    session = await session_manager.get_session("cleanup_test_001")
    assert session is None


@pytest.mark.asyncio
async def test_get_messages_for_llm(session_manager):
    """测试获取 LLM 格式的消息"""
    dialog_id = "llm_test_001"

    await session_manager.create_session(dialog_id)
    await session_manager.add_user_message(dialog_id, "Hello")
    await session_manager.start_ai_response(dialog_id, "msg_001")
    await session_manager.complete_ai_response(dialog_id, "msg_001", "Hi!")

    # 获取 LLM 格式消息
    messages = await session_manager.get_messages_for_llm(dialog_id, max_tokens=8000)

    assert len(messages) == 2
    assert messages[0]["type"] == "human"
    assert messages[1]["type"] == "ai"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
