# 迁移指南：从旧架构到新架构

## 概述

本指南帮助你将代码从旧架构（`WebSocketBridge` + `SQLAgentLoopV2`）迁移到新架构（`BaseInteractiveAgent`）。

## 迁移对比表

| 场景 | 旧架构 | 新架构 |
|------|--------|--------|
| 初始化 Agent | 30+ 行 | 3 行 |
| 发送用户消息 | 手动调用 WebSocketBridge | `add_user_message()` |
| 流式输出 | 管理回调 + 消息 ID | `assistant_stream()` 上下文 |
| 工具调用 | 手动发送调用和结果 | `tool_execution()` 上下文 |
| 消息收口 | 手动调用 finalize | `finalize_session()` |

## 步骤一：替换导入

### 旧代码

```python
from agents.websocket.bridge import WebSocketBridge
from agents.sql_agent_loop_v2 import SQLAgentLoopV2, MASTER_SYSTEM
from agents.utils import is_stop_requested
```

### 新代码

```python
from agents.base import BaseInteractiveAgent, AgentType
from agents.sql_agent_interactive import InteractiveSQLAgent, MASTER_SYSTEM
```

## 步骤二：重构 Agent 初始化

### 旧代码

```python
async def process_request(dialog_id: str):
    # 创建桥接器
    bridge = WebSocketBridge(dialog_id, agent_type="master")
    await bridge.initialize(title="Skill Agent")

    # 定义回调
    def _on_after_round(messages, response):
        bridge.on_after_round(messages, response)
        append_messages_jsonl(messages, LOG_DIR, LOG_FILE)

    def _on_stop(messages, response):
        bridge.on_stop(messages, response)
        append_messages_jsonl(messages, LOG_DIR, LOG_FILE)

    # 创建 Agent
    agent = SQLAgentLoopV2(
        client=client,
        model=model,
        system=MASTER_SYSTEM,
        max_tokens=8000,
        max_rounds=30,
        enable_learning=True,
        # 大量回调配置
        on_before_round=bridge.on_before_round,
        on_stream_token=None,
        on_stream_text=bridge.on_stream_text,
        on_tool_call=bridge.on_tool_call,
        on_tool_result=bridge.on_tool_result,
        on_round_end=bridge.on_round_end,
        on_after_round=_on_after_round,
        on_stop=_on_stop,
        should_stop=lambda: is_stop_requested(agent_state),
    )
```

### 新代码

```python
async def process_request(dialog_id: str):
    # 一行创建 Agent
    agent = InteractiveSQLAgent(
        client=client,
        model=model,
        dialog_id=dialog_id,
        system=MASTER_SYSTEM,
        max_tokens=8000,
        max_rounds=30,
        enable_learning=True,
    )
```

## 步骤三：重构消息发送

### 旧代码

```python
from agents.websocket.event_manager import RealTimeMessage, MessageType, MessageStatus

message = RealTimeMessage(
    id=str(uuid.uuid4()),
    type=MessageType.USER_MESSAGE,
    content=content,
    status=MessageStatus.COMPLETED,
)
event_manager.add_message_to_dialog(dialog_id, message)
```

### 新代码

```python
# 在 Agent 类内部
agent.add_user_message(content)

# 或者使用 bridge
agent.bridge.create_user_message(content)
```

## 步骤四：重构流式输出

### 旧代码

```python
# 手动管理消息 ID
if not bridge._current_assistant_message_id:
    message = asyncio.run_coroutine_threadsafe(
        bridge.message_bridge.start_assistant_response(),
        loop
    ).result(timeout=5)
    bridge._current_assistant_message_id = message.id

# 发送 token
asyncio.run_coroutine_threadsafe(
    bridge.message_bridge.send_stream_token(token),
    loop
)

# 完成消息
asyncio.run_coroutine_threadsafe(
    bridge.message_bridge.complete_assistant_response(final_content),
    loop
).result(timeout=5)
```

### 新代码

```python
# 使用上下文管理器
with agent.assistant_stream():
    for token in tokens:
        if agent.state.stop_requested:
            break
        agent.stream_text(token)
# 自动完成
```

## 步骤五：重构工具调用

### 旧代码

```python
def on_tool_call(tool_name: str, tool_input: dict, messages: list):
    # 发送工具调用
    message = asyncio.run_coroutine_threadsafe(
        bridge.message_bridge.send_tool_call(tool_name, tool_input),
        loop
    ).result(timeout=5)
    current_tool_id = message.id

def on_tool_result(block, output: str, results: list, messages: list):
    # 发送工具结果
    asyncio.run_coroutine_threadsafe(
        bridge.message_bridge.send_tool_result(current_tool_id, output),
        loop
    ).result(timeout=5)
```

### 新代码

```python
with agent.tool_execution("sql_query", {"sql": sql}) as tool:
    result = execute_sql(tool.tool_input)
    tool.complete(result)
# 自动发送调用和结果
```

## 步骤六：重构停止机制

### 旧代码

```python
# 全局状态
agent_state = {
    "stop_requested": False,
}

def is_stop_requested(state):
    return bool(state.get("stop_requested", False))

# Agent 配置
agent = SQLAgentLoopV2(
    should_stop=lambda: is_stop_requested(agent_state),
)

# 停止请求
agent_state["stop_requested"] = True
```

### 新代码

```python
# 内置状态管理
agent = InteractiveSQLAgent(...)

# 停止请求
agent.request_stop()
# 或
agent.state.stop()

# 检查停止
if agent.state.check_should_stop():
    return
```

## 步骤七：重构消息收口

### 旧代码

```python
try:
    if bridge.message_bridge and bridge._loop:
        asyncio.run_coroutine_threadsafe(
            bridge.message_bridge.finalize_streaming_messages(),
            bridge._loop,
        ).result(timeout=5)
except Exception as e:
    logger.info(f"finalize failed: {e}")
```

### 新代码

```python
agent.finalize_session()  # 自动处理
```

## 完整示例对比

### 旧架构完整代码

```python
# main_old.py
async def process_agent_request(dialog_id: str):
    if agent_state["is_running"]:
        return

    agent_state["is_running"] = True
    agent_state["current_dialog_id"] = dialog_id
    agent_state["stop_requested"] = False

    bridge = WebSocketBridge(dialog_id, agent_type="master")
    await bridge.initialize(title="Skill Agent")

    def _on_after_round(messages, response):
        bridge.on_after_round(messages, response)
        append_messages_jsonl(messages, LOG_DIR, LOG_FILE)

    def _on_stop(messages, response):
        bridge.on_stop(messages, response)
        append_messages_jsonl(messages, LOG_DIR, LOG_FILE)

    try:
        await _send_system_event(dialog_id, "开始处理")

        dialog = event_manager.get_dialog(dialog_id)
        messages = build_model_messages_from_dialog(dialog.messages)

        agent = SQLAgentLoopV2(
            client=agent_state["client"],
            model=agent_state["model"],
            system=MASTER_SYSTEM,
            max_tokens=8000,
            max_rounds=30,
            enable_learning=True,
            on_before_round=bridge.on_before_round,
            on_stream_token=None,
            on_stream_text=bridge.on_stream_text,
            on_tool_call=bridge.on_tool_call,
            on_tool_result=bridge.on_tool_result,
            on_round_end=bridge.on_round_end,
            on_after_round=_on_after_round,
            on_stop=_on_stop,
            should_stop=lambda: is_stop_requested(agent_state),
        )

        await asyncio.to_thread(agent.run, messages)
        await _send_system_event(dialog_id, "处理完成")

    except Exception as e:
        logger.error(f"Error: {e}")
        await _send_system_event(dialog_id, f"错误: {e}")
    finally:
        try:
            if bridge.message_bridge and bridge._loop:
                asyncio.run_coroutine_threadsafe(
                    bridge.message_bridge.finalize_streaming_messages(),
                    bridge._loop,
                ).result(timeout=5)
        except Exception as e:
            logger.info(f"finalize failed: {e}")

        agent_state["is_running"] = False
        agent_state["current_dialog_id"] = None
```

### 新架构完整代码

```python
# main_new.py
async def process_agent_request(dialog_id: str):
    if agent_state["is_running"]:
        return

    agent_state["is_running"] = True
    agent_state["current_dialog_id"] = dialog_id
    agent_state["stop_requested"] = False

    try:
        dialog = event_manager.get_dialog(dialog_id)
        messages = build_model_messages_from_dialog(dialog.messages)

        agent = InteractiveSQLAgent(
            client=agent_state["client"],
            model=agent_state["model"],
            dialog_id=dialog_id,
            system=MASTER_SYSTEM,
            max_tokens=8000,
            max_rounds=30,
            enable_learning=True,
        )

        await asyncio.to_thread(agent.run_conversation, messages)

    except Exception as e:
        logger.error(f"Error: {e}")
        agent.send_error(str(e))
    finally:
        agent_state["is_running"] = False
        agent_state["current_dialog_id"] = None
```

**代码量减少约 70%**

## 常见问题

### Q: 新架构是否完全替代 WebSocket 层？

A: 不是。WebSocket 层仍然是基础设施，但业务代码不再直接与其交互，而是通过 `BaseInteractiveAgent` 间接使用。

### Q: 可以混合使用新旧架构吗？

A: 可以。新旧架构可以共存，逐步迁移。旧代码继续使用 `SQLAgentLoopV2`，新代码使用 `InteractiveSQLAgent`。

### Q: 如何调试新架构的消息流？

A: `BaseInteractiveAgent` 会自动记录日志，查看日志中的 `[FrontendBridge]` 和 `[BaseInteractiveAgent]` 标签即可。

### Q: 前端需要修改吗？

A: 不需要。新架构保持与前端的数据格式兼容，前端无需任何改动。
