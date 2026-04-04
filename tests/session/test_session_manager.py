"""
测试 DialogSessionManager 与 Runtime 的集成
"""

import pytest
import asyncio
from backend.domain.models.dialog import DialogSessionManager, SessionStatus
from backend.domain.models.dialog.session import SessionEvent


@pytest.fixture
def session_manager():
    """创建测试用的 SessionManager"""
    return DialogSessionManager(max_sessions=10, session_ttl_seconds=300)


@pytest.fixture
def event_collector():
    """收集事件的 fixture"""
    events = []

    async def handler(event: SessionEvent):
        events.append(event)

    return events, handler


@pytest.mark.asyncio
async def test_create_session(session_manager):
    """测试创建会话"""
    session = await session_manager.create_session("dlg_001", "Test Dialog")

    assert session.dialog_id == "dlg_001"
    assert session.metadata.title == "Test Dialog"
    assert session.status == SessionStatus.ACTIVE
    assert session.message_count == 0


@pytest.mark.asyncio
async def test_add_user_message(session_manager):
    """测试添加用户消息"""
    await session_manager.create_session("dlg_001")
    msg = await session_manager.add_user_message("dlg_001", "Hello, AI!")

    assert msg.content == "Hello, AI!"

    session = await session_manager.get_session("dlg_001")
    assert session.message_count == 1
    assert session.status == SessionStatus.ACTIVE


@pytest.mark.asyncio
async def test_ai_response_flow(session_manager, event_collector):
    """测试 AI 响应完整流程"""
    events, handler = event_collector
    session_manager.set_event_handler(handler)

    # 创建会话
    await session_manager.create_session("dlg_001")

    # 添加用户消息
    await session_manager.add_user_message("dlg_001", "Hello")

    # 开始 AI 响应
    await session_manager.start_ai_response("dlg_001", "msg_001")

    session = await session_manager.get_session("dlg_001")
    assert session.status == SessionStatus.STREAMING
    assert session.streaming_context.message_id == "msg_001"

    # 模拟流式 delta（不存储）
    await session_manager.emit_delta("dlg_001", "msg_001", "Hi")
    await session_manager.emit_delta("dlg_001", "msg_001", " there")

    # 完成 AI 响应
    await session_manager.complete_ai_response("dlg_001", "msg_001", "Hi there!")

    session = await session_manager.get_session("dlg_001")
    assert session.status == SessionStatus.COMPLETED
    assert session.message_count == 2  # user + ai
    assert session.streaming_context is None

    # 验证事件
    assert len(events) > 0
    event_types = [e.type for e in events]
    assert "status_change" in event_types
    assert "delta" in event_types
    assert "completed" in event_types


@pytest.mark.asyncio
async def test_session_lifecycle(session_manager):
    """测试会话完整生命周期"""
    # 创建
    session = await session_manager.create_session("dlg_001")
    assert session.status == SessionStatus.ACTIVE

    # 关闭
    await session_manager.close_session("dlg_001")

    # 验证已关闭
    closed_session = await session_manager.get_session("dlg_001")
    assert closed_session is None


@pytest.mark.asyncio
async def test_get_messages_for_llm(session_manager):
    """测试获取 LLM 格式的消息"""
    await session_manager.create_session("dlg_001")
    await session_manager.add_user_message("dlg_001", "Hello")
    await session_manager.start_ai_response("dlg_001", "msg_001")
    await session_manager.complete_ai_response("dlg_001", "msg_001", "Hi!")

    messages = await session_manager.get_messages_for_llm("dlg_001")

    assert len(messages) == 2
    assert messages[0]["type"] == "human"
    assert messages[1]["type"] == "ai"


@pytest.mark.asyncio
async def test_build_snapshot(session_manager):
    """测试构建前端快照"""
    await session_manager.create_session("dlg_001", "Test Dialog")
    await session_manager.add_user_message("dlg_001", "Hello")

    snapshot = session_manager.build_snapshot("dlg_001")

    assert snapshot is not None
    assert snapshot["id"] == "dlg_001"
    assert snapshot["title"] == "Test Dialog"
    assert len(snapshot["messages"]) == 1
    assert snapshot["status"] == SessionStatus.ACTIVE.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
