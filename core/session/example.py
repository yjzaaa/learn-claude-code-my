"""
DialogSessionManager 使用示例

演示如何在不累积 delta 的情况下管理对话会话。
"""

import asyncio
from core.session import DialogSessionManager, SessionEvent


async def basic_usage_example():
    """
    基础使用示例
    """
    print("=" * 50)
    print("基础使用示例")
    print("=" * 50)

    # 创建 Manager
    mgr = DialogSessionManager()

    # 1. 创建对话
    session = mgr.create("Test Conversation")
    print(f"✓ 创建对话: {session.id}")

    # 2. 添加用户消息
    mgr.add_user_message(session.id, "Hello, how are you?")
    print("✓ 添加用户消息")

    # 3. 开始流式 (仅标记状态)
    mgr.start_streaming(session.id, "msg_001")
    print("✓ 开始流式响应")

    # 4. 转发 delta (不存储，直接透传给前端)
    await mgr.emit_delta(session.id, "msg_001", "I'm ")
    await mgr.emit_delta(session.id, "msg_001", "doing ")
    await mgr.emit_delta(session.id, "msg_001", "great!")
    print("✓ 转发 delta 片段 (不存储)")

    # 5. 完成流式，添加完整消息
    msg = mgr.complete_streaming(session.id, "I'm doing great!")
    print(f"✓ 完成流式，添加完整消息: {msg.content[:30]}...")

    # 6. 查看会话状态
    snapshot = mgr.build_snapshot(session.id)
    print(f"\n会话快照:")
    print(f"  - 消息数: {snapshot['metadata']['message_count']}")
    print(f"  - 状态: {snapshot['status']}")
    print(f"  - 消息列表: {[m['role'] for m in snapshot['messages']]}")

    return session.id


async def event_handler_example():
    """
    事件处理器示例

    演示如何接收并处理 SessionManager 发出的事件。
    """
    print("\n" + "=" * 50)
    print("事件处理器示例")
    print("=" * 50)

    events_log = []

    async def my_handler(event: SessionEvent):
        """自定义事件处理器"""
        events_log.append(event)
        print(f"  [Event] {event.type}: {list(event.data.keys())}")

    # 创建带事件处理器的 Manager
    mgr = DialogSessionManager(event_handler=my_handler)

    # 创建对话并操作
    session = mgr.create("Event Test")
    mgr.add_user_message(session.id, "Hi")
    mgr.start_streaming(session.id, "msg_001")

    # 注意：delta 转发是异步的，需要等待
    await mgr.emit_delta(session.id, "msg_001", "Hello!")

    mgr.complete_streaming(session.id, "Hello! Nice to meet you.")

    print(f"\n✓ 总共收到 {len(events_log)} 个事件")


async def streaming_abort_example():
    """
    流式中止示例
    """
    print("\n" + "=" * 50)
    print("流式中止示例")
    print("=" * 50)

    mgr = DialogSessionManager()
    session = mgr.create("Abort Test")

    mgr.add_user_message(session.id, "Tell me a story")
    mgr.start_streaming(session.id, "msg_001")

    print("✓ 开始流式...")

    # 模拟中途中止
    mgr.abort_streaming(session.id, "User cancelled")

    print(f"✓ 中止后状态: {mgr.get(session.id).status}")
    print(f"✓ 消息数 (未添加不完整消息): {len(mgr.get(session.id).messages)}")


async def multiple_conversations_example():
    """
    多对话管理示例
    """
    print("\n" + "=" * 50)
    print("多对话管理示例")
    print("=" * 50)

    mgr = DialogSessionManager()

    # 创建多个对话
    s1 = mgr.create("Conversation 1")
    s2 = mgr.create("Conversation 2")
    s3 = mgr.create("Conversation 3")

    # 给每个对话添加消息
    mgr.add_user_message(s1.id, "Message in conv 1")
    mgr.add_user_message(s2.id, "Message in conv 2")

    mgr.add_assistant_message(s1.id, "Response in conv 1")
    mgr.add_assistant_message(s2.id, "Response in conv 2")

    # 列出所有对话 (按更新时间倒序)
    all_sessions = mgr.list_all()
    print(f"✓ 总共 {len(all_sessions)} 个对话")
    for s in all_sessions:
        print(f"  - {s.title}: {s.message_count} 条消息")

    # 关闭一个对话
    mgr.close(s3.id)
    print(f"✓ 关闭后剩余: {len(mgr.list_all())} 个对话")


async def full_integration_example():
    """
    完整集成示例

    演示如何在 WebSocket 场景中使用。
    """
    print("\n" + "=" * 50)
    print("完整集成示例 (WebSocket 场景)")
    print("=" * 50)

    # 模拟 WebSocket 发送
    websocket_messages = []

    async def websocket_sender(event: SessionEvent):
        """模拟发送到 WebSocket"""
        websocket_messages.append({
            "type": event.type,
            "dialog_id": event.dialog_id,
            "data": event.data,
        })

    mgr = DialogSessionManager(event_handler=websocket_sender)

    # 模拟用户发送消息
    dialog_id = mgr.create("WebSocket Test").id
    mgr.add_user_message(dialog_id, "What's the weather?")

    # 模拟 Agent 流式响应
    message_id = "msg_weather_001"
    mgr.start_streaming(dialog_id, message_id)

    # 模拟接收 delta (通常来自 LLM 流式 API)
    deltas = ["The ", "weather ", "is ", "sunny ", "today."]
    for delta in deltas:
        await mgr.emit_delta(dialog_id, message_id, delta)

    # 完成响应
    full_content = "".join(deltas)
    mgr.complete_streaming(dialog_id, full_content)

    # 打印 WebSocket 收到的消息
    print(f"✓ WebSocket 收到 {len(websocket_messages)} 条消息:")
    for msg in websocket_messages:
        print(f"  - {msg['type']}: {list(msg['data'].keys())}")

    # 最终快照
    snapshot = mgr.build_snapshot(dialog_id)
    print(f"\n✓ 最终对话状态:")
    print(f"  - 消息: {[(m['role'], m['content'][:20]) for m in snapshot['messages']]}")


async def main():
    """运行所有示例"""
    await basic_usage_example()
    await event_handler_example()
    await streaming_abort_example()
    await multiple_conversations_example()
    await full_integration_example()

    print("\n" + "=" * 50)
    print("所有示例完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
