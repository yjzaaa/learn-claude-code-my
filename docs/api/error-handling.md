# 错误处理标准

## 错误码规范

### 格式

```
CATEGORY_CODE
```

- **CATEGORY**: 错误类别 (大写字母)
- **CODE**: 3位数字编码

### 错误类别

| 类别 | HTTP 状态码 | 说明 |
|------|-------------|------|
| `VALIDATION` | 400 | 请求验证错误 |
| `AUTH` | 401/403 | 认证/授权错误 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `CONFLICT` | 409 | 资源冲突 |
| `RATE_LIMIT` | 429 | 限流错误 |
| `INTERNAL` | 500 | 内部服务器错误 |
| `AGENT` | 600 | Agent 特定错误 |
| `TOOL` | 700 | 工具执行错误 |
| `SKILL` | 800 | Skill 相关错误 |

### 编码范围

| 范围 | 用途 |
|------|------|
| 001-099 | 通用错误 |
| 100-199 | Dialog 相关 |
| 200-299 | Message 相关 |
| 300-399 | Agent 相关 |
| 400-499 | Tool 相关 |
| 500-599 | Skill 相关 |

---

## 错误码列表

### 验证错误 (VALIDATION)

| 错误码 | 说明 | 场景 |
|--------|------|------|
| `VALIDATION_001` | 请求参数无效 | 参数类型错误、格式错误 |
| `VALIDATION_002` | 缺少必需参数 | 必填字段缺失 |

### 未找到 (NOT_FOUND)

| 错误码 | 说明 | 场景 |
|--------|------|------|
| `NOT_FOUND_100` | 对话不存在 | 访问不存在的对话 |
| `NOT_FOUND_101` | 消息不存在 | 访问不存在的消息 |
| `NOT_FOUND_200` | 工具不存在 | 调用不存在的工具 |
| `NOT_FOUND_500` | Skill 不存在 | 加载不存在的 Skill |

### 冲突 (CONFLICT)

| 错误码 | 说明 | 场景 |
|--------|------|------|
| `CONFLICT_100` | 对话正在处理中 | 向正在处理的对话发送消息 |

### 内部错误 (INTERNAL)

| 错误码 | 说明 | 场景 |
|--------|------|------|
| `INTERNAL_001` | 内部服务器错误 | 未预期的服务器错误 |

### Agent 错误 (AGENT)

| 错误码 | 说明 | 场景 |
|--------|------|------|
| `AGENT_300` | Agent 执行错误 | Agent 执行过程中出错 |
| `AGENT_301` | Agent 超时 | Agent 执行超时 |
| `AGENT_302` | Agent 轮次限制达到 | 达到最大对话轮次 |

### 工具错误 (TOOL)

| 错误码 | 说明 | 场景 |
|--------|------|------|
| `TOOL_400` | 工具执行错误 | 工具执行失败 |
| `TOOL_401` | 工具未找到 | 调用的工具不存在 |
| `TOOL_402` | 工具参数无效 | 工具参数验证失败 |

### Skill 错误 (SKILL)

| 错误码 | 说明 | 场景 |
|--------|------|------|
| `SKILL_500` | Skill 加载错误 | Skill 加载失败 |
| `SKILL_501` | Skill 未找到 | 请求的 Skill 不存在 |

---

## 错误响应格式

### REST API 错误响应

```json
{
  "success": false,
  "message": "Dialog not found",
  "error": {
    "code": "NOT_FOUND_100",
    "details": {
      "dialog_id": "dlg_nonexistent"
    }
  }
}
```

### WebSocket 错误事件

```json
{
  "type": "error",
  "dialog_id": "dlg_abc123",
  "error": {
    "code": "AGENT_300",
    "message": "Agent execution failed",
    "details": {
      "error": "Connection timeout"
    }
  },
  "timestamp": 1711800000000
}
```

---

## 错误处理指南

### 服务端处理

#### Python (FastAPI)

```python
from fastapi import HTTPException
from docs.api.types import ErrorCode, create_error_response

# REST API 错误
@app.get("/api/dialogs/{dialog_id}")
def get_dialog(dialog_id: str):
    dialog = find_dialog(dialog_id)
    if not dialog:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "message": "Dialog not found",
                "error": {
                    "code": ErrorCode.NOT_FOUND_100.value,
                    "details": {"dialog_id": dialog_id}
                }
            }
        )
    return {"success": True, "data": dialog}

# WebSocket 错误
async def handle_agent_error(dialog_id: str, error: Exception):
    error_event = create_error_response(
        ErrorCode.AGENT_300,
        details={"error": str(error)}
    )
    error_event.dialog_id = dialog_id
    await broadcast(error_event.model_dump())
```

### 客户端处理

#### TypeScript/React

```typescript
import { ErrorCode, ErrorMessages, isErrorEvent } from '@/types/api';

// 处理 REST API 错误
async function fetchDialog(dialogId: string) {
  const response = await fetch(`/api/dialogs/${dialogId}`);
  const data = await response.json();

  if (!data.success) {
    const errorCode = data.error?.code as ErrorCode;
    const message = ErrorMessages[errorCode] || data.message;

    // 根据错误码处理
    switch (errorCode) {
      case ErrorCode.NOT_FOUND_100:
        // 跳转回列表页
        router.push('/dialogs');
        break;
      case ErrorCode.CONFLICT_100:
        // 显示忙状态
        showBusyState();
        break;
      default:
        toast.error(message);
    }

    throw new Error(message);
  }

  return data.data;
}

// 处理 WebSocket 错误
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (isErrorEvent(data)) {
    const { code, message } = data.error;

    // 记录错误
    console.error(`[WS Error] ${code}: ${message}`);

    // 根据错误码处理
    switch (code) {
      case ErrorCode.AGENT_302:
        // 轮次限制，提示用户
        showRoundsLimitDialog();
        break;
      case ErrorCode.TOOL_400:
        // 工具错误，显示在 UI
        appendToolError(data.dialog_id, message);
        break;
      default:
        toast.error(message);
    }
  }
};
```

---

## 错误恢复策略

### 自动重试

| 错误码 | 重试策略 | 说明 |
|--------|----------|------|
| `INTERNAL_001` | 指数退避，最多3次 | 服务器临时错误 |
| `AGENT_301` | 不重试，提示用户 | 超时需要用户确认 |
| `TOOL_400` | 不重试 | 工具执行失败 |

### 重连策略

WebSocket 断线重连：

```typescript
const RECONNECT_CONFIG = {
  initialDelay: 1000,      // 首次重连延迟 1s
  maxDelay: 30000,         // 最大延迟 30s
  maxAttempts: 10,         // 最大重试次数
  backoffMultiplier: 2,    // 退避倍数
};

function calculateReconnectDelay(attempt: number): number {
  const delay = RECONNECT_CONFIG.initialDelay *
    Math.pow(RECONNECT_CONFIG.backoffMultiplier, attempt);
  return Math.min(delay, RECONNECT_CONFIG.maxDelay);
}
```

---

## 监控与日志

### 错误日志格式

```python
{
    "timestamp": "2024-03-30T12:00:00Z",
    "level": "error",
    "error_code": "AGENT_300",
    "dialog_id": "dlg_abc123",
    "message": "Agent execution failed",
    "details": {
        "exception": "ConnectionTimeout",
        "stack_trace": "..."
    },
    "request_id": "req_xyz789"
}
```

### 关键指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| `error_rate` | 错误率 | > 5% |
| `agent_timeout_rate` | Agent 超时率 | > 1% |
| `ws_reconnect_rate` | WebSocket 重连率 | > 10% |
