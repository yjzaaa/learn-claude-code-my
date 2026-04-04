# 修复流式消息 complete 事件问题

## 问题描述

`deep_runtime.py` 向前端发送流式消息时，最后一个 delta 数据会覆盖返回的完整 AIMessage。

## 根本原因

### 1. 缺少 `complete` 事件

在 `send_message` 方法中，`complete` 事件被注释掉了：

```python
# 第 454 行（修复前）
# yield AgentEvent(type="complete", data=None)  # ← 被注释！
```

### 2. 前端无法确定流式结束

前端通过 `text_delta` 事件接收增量数据：
```javascript
// 前端逻辑
let content = '';
for (const event of stream) {
  if (event.type === 'text_delta') {
    content += event.data;  // 累积增量数据
  }
  // 没有 complete 事件，无法确定何时停止
}
```

由于没有 `complete` 事件，前端可能：
- 只显示最后一个 delta 的内容
- 或者无法正确渲染完整消息

## 修复方案

### 修复内容

```python
# 第 454-458 行（修复后）
# 流结束，发送 complete 事件（包含完整消息内容）
self._update_logger.info("Agent stream complete, yielding complete event")
if accumulated_content:
    # 发送完整消息内容，帮助前端正确显示
    yield AgentEvent(type="complete", data={"full_content": accumulated_content})
```

### 事件序列

修复后的完整事件序列：

```
User Input
    ↓
Agent 处理
    ↓
Stream Events:
    ├─ text_delta: {data: "Hello"}
    ├─ text_delta: {data: ", "}
    ├─ text_delta: {data: "world"}
    ├─ text_delta: {data: "!"}
    └─ complete: {full_content: "Hello, world!"}  ← 新增
    ↓
前端显示完整消息
```

## 前端适配建议

### 方案 1：使用 complete 事件重置内容（推荐）

```javascript
let accumulatedContent = '';

for await (const event of agentStream) {
  switch (event.type) {
    case 'text_delta':
      accumulatedContent += event.data;
      // 可以实时显示累积内容
      displayMessage(accumulatedContent);
      break;
      
    case 'complete':
      // 使用服务器返回的完整内容确认显示
      if (event.data?.full_content) {
        displayMessage(event.data.full_content);
      }
      break;
      
    case 'error':
      displayError(event.data);
      break;
  }
}
```

### 方案 2：只使用 delta 累积（简单场景）

```javascript
let content = '';

for await (const event of agentStream) {
  if (event.type === 'text_delta') {
    content += event.data;
    displayMessage(content);
  }
  // 忽略 complete 事件，只依赖 delta 累积
}
```

## 注意事项

### 1. 工具调用场景

当 Agent 调用工具时，LangGraph 会：
1. 流式返回 LLM 思考过程（AIMessage）
2. 执行工具
3. 再次调用 LLM

代码已正确处理这种场景：
```python
if is_last_chunk:
    # 保存消息到历史
    dialog.add_ai_message(accumulated_content, msg_id=message_id)
    # 继续流式输出（不中断）
```

### 2. 多消息场景

如果 Agent 在一次调用中返回多条消息（例如有工具调用后再次生成内容），`accumulated_content` 会在每次新消息开始时重置：

```python
current_msg_id = getattr(message_chunk, 'id', None)
if current_msg_id and current_msg_id != last_message_id:
    if last_message_id is not None:
        accumulated_content = ""  # 重置累积内容
    last_message_id = current_msg_id
```

### 3. complete 事件数据格式

```typescript
interface CompleteEvent {
  type: "complete";
  data: {
    full_content: string;  // 完整的消息内容
  };
}
```

## 验证测试

### 测试用例 1：简单对话

```python
async for event in runtime.send_message(dialog_id, "Hello"):
    print(f"Event: {event.type}, Data: {event.data}")

# 预期输出：
# Event: text_delta, Data: "Hi"
# Event: text_delta, Data: " there"
# Event: text_delta, Data: "!"
# Event: complete, Data: {"full_content": "Hi there!"}
```

### 测试用例 2：工具调用

```python
async for event in runtime.send_message(dialog_id, "Read file.txt"):
    print(f"Event: {event.type}")

# 预期输出：
# Event: text_delta  (LLM 思考过程)
# Event: complete   (第一次调用完成)
# ... 工具执行 ...
# Event: text_delta  (LLM 生成结果)
# Event: complete   (第二次调用完成)
```

## 相关代码位置

- 文件：`core/agent/runtimes/deep_runtime.py`
- 方法：`send_message`
- 行号：454-458（修复后）
