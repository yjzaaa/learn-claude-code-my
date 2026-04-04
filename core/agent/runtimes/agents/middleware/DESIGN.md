# Claude Code 压缩机制移植设计文档

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    AgentBuilder (扩展)                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  .with_claude_compression(level="standard")              │   │
│  │  .with_micro_compact_only()                             │   │
│  │  .with_aggressive_compression()                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│           ClaudeCompressionMiddleware                           │
│           (AgentMiddleware 实现)                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  统一使用 deep-agent Backend 存储系统                     │   │
│  │  - Session Memory 存储会话历史                            │   │
│  │  - Compression History 存储压缩事件                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────┬───────────┬───────────┬───────────┬─────────────────────┘
        │           │           │           │
        ▼           ▼           ▼           ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│   Micro   │ │   Auto    │ │  Partial  │ │  Session  │
│  Compact  │ │  Compact  │ │  Compact  │ │  Memory   │
│  Strategy │ │  Strategy │ │  Strategy │ │  Strategy │
└───────────┘ └───────────┘ └───────────┘ └───────────┘
        │           │           │           │
        ▼           ▼           ▼           ▼
   清理旧工具   Token阈值    智能保留    Backend存储
   结果缓存    自动压缩     关键内容    会话历史
```

## Backend 统一存储

### 设计原则

**所有持久化操作统一使用 deep-agent BackendProtocol**：
- ✅ Session Memory 存储到 Backend
- ✅ Compression History 存储到 Backend
- ✅ 支持所有 Backend 实现（Filesystem, State, Daytona, etc.）
- ✅ 同步/异步 API 完整支持

### Backend 存储路径

```
/compression_history/
├── session_{session_id}_{timestamp}.json     # 会话历史
├── {session_id}_history.json                  # 压缩事件历史
└── ...
```

### Backend 接口使用

```python
# 写入会话数据
result = backend.write(
    "/compression_history/session_xxx.json",
    json.dumps(session_data)
)

# 读取会话数据
responses = backend.download_files(["/compression_history/session_xxx.json"])
content = responses[0].content

# 异步写入
result = await backend.awrite(path, content)
```

## 核心组件

### 1. ClaudeCompressionMiddleware

实现 `AgentMiddleware` 接口，作为 deep-agent 框架的中间件。

**Backend 集成点**：
```python
def _get_backend(self, request: ModelRequest):
    """从 request 获取 Backend"""
    runtime = getattr(request, "runtime", None)
    if runtime and hasattr(runtime, "backend"):
        return runtime.backend
    return request.state.get("_backend")

# 保存压缩历史
file_path = self.save_compression_history(backend, session_id, state)

# 异步保存
file_path = await self.asave_compression_history(backend, session_id, state)
```

### 2. SessionMemoryStrategy

**使用 Backend 存储会话**：
```python
def _save_to_backend(self, backend, session_id, messages, summary):
    """使用 deep-agent Backend 统一存储"""
    file_path = f"/compression_history/session_{session_id}_{timestamp}.json"

    session_data = {
        "session_id": session_id,
        "timestamp": timestamp,
        "summary": summary,
        "message_count": len(messages),
        "messages": [...]
    }

    # 使用 Backend 写入
    result = backend.write(file_path, json.dumps(session_data))

    if result.error:
        logger.warning(f"Failed to save: {result.error}")
        return None

    return file_path
```

### 3. 支持的 Backend 类型

| Backend 类型 | 存储位置 | 适用场景 |
|-------------|---------|---------|
| `FilesystemBackend` | 本地文件系统 | 开发、单机部署 |
| `StateBackend` | LangGraph 状态 | 状态持久化 |
| `DaytonaSandbox` | 远程沙箱 | 云端部署 |
| `MemorySaver` | 内存 | 测试、临时会话 |
| 自定义 Backend | 任意 | 企业级定制 |

## 使用示例

### 基础用法（自动获取 Backend）

```python
from core.agent.runtimes.agents import AgentBuilder

agent = (
    AgentBuilder()
    .with_model("claude-sonnet-4-6")
    .with_tools(tools)
    .with_backend(backend)  # Backend 会自动传递给压缩中间件
    .with_claude_compression(level="standard")
    .build()
)
```

### 手动传递 Backend

```python
# 如果需要显式传递 Backend
middleware = ClaudeCompressionMiddleware(
    enable_session_memory=True,
)

# 后续手动保存压缩历史
file_path = middleware.save_compression_history(
    backend=backend,
    session_id="session_123",
    state=agent_state,
)
```

### 不同 Backend 配置

```python
# 1. 文件系统 Backend（开发环境）
from deepagents.backends import FilesystemBackend

backend = FilesystemBackend(root_dir="./data")
agent = (
    AgentBuilder()
    .with_backend(backend)
    .with_claude_compression(level="standard")
    .build()
)
# 存储位置: ./data/compression_history/session_xxx.json

# 2. State Backend（生产环境）
from deepagents.backends import StateBackend

backend = StateBackend
agent = (
    AgentBuilder()
    .with_backend(backend)
    .with_claude_compression(level="standard")
    .build()
)
# 存储位置: LangGraph 状态中的 /compression_history/

# 3. Daytona Sandbox（云端）
from daytona import Daytona
from langchain_daytona import DaytonaSandbox

sandbox = Daytona().create()
backend = DaytonaSandbox(sandbox=sandbox)
agent = (
    AgentBuilder()
    .with_backend(backend)
    .with_claude_compression(level="standard")
    .build()
)
# 存储位置: Daytona 沙箱中的 /compression_history/
```

## 存储格式

### 会话历史 (session_{id}_{timestamp}.json)

```json
{
  "session_id": "uuid",
  "timestamp": "2024-01-01T00:00:00Z",
  "summary": "Files: a.py, b.py; Tasks: 3 items",
  "message_count": 100,
  "messages": [
    {"type": "HumanMessage", "content": "..."},
    {"type": "AIMessage", "content": "..."}
  ]
}
```

### 压缩历史 ({session_id}_history.json)

```json
{
  "session_id": "uuid",
  "timestamp": "2024-01-01T00:00:00Z",
  "stats": {
    "total_compactions": 5,
    "total_tokens_saved": 50000,
    "by_level": {
      "micro": {"count": 3, "tokens_saved": 5000},
      "auto": {"count": 2, "tokens_saved": 45000}
    }
  },
  "events": [
    {
      "level": "auto",
      "timestamp": "2024-01-01T00:00:00Z",
      "original_message_count": 100,
      "compressed_message_count": 60,
      "original_token_count": 150000,
      "compressed_token_count": 80000,
      "file_path": null
    }
  ]
}
```

## 与 deep-agent 原生压缩对比

| 特性 | deep-agent SummarizationMiddleware | ClaudeCompressionMiddleware |
|------|-----------------------------------|----------------------------|
| **存储方式** | Backend 存储 | ✅ 相同的 Backend 存储 |
| **压缩层级** | 单层（参数截断+摘要） | 4层渐进式 |
| **微压缩** | 简单参数截断 | ✅ 工具结果缓存管理 |
| **Session Memory** | Backend 存储 | ✅ 相同的 Backend API |
| **压缩历史** | 无 | ✅ Backend 存储 |
| **统计信息** | 基础 | ✅ 详细的压缩事件 |

## 配置选项

```python
CompressionConfig(
    # 启用层级
    enable_micro_compact=True,
    enable_auto_compact=True,
    enable_partial_compact=False,
    enable_session_memory=False,

    # 会话记忆配置（Backend 存储）
    session=SessionMemoryConfig(
        storage_path_prefix="/compression_history",  # Backend 存储路径
        enable_cross_session_recovery=True,
        save_to_backend=True,  # 使用 Backend 存储
    ),
)
```

## 注意事项

1. **Backend 必须可用**：如果 Backend 为 None，压缩仍然工作，但历史不会持久化
2. **权限检查**：Backend 写入失败会记录 warning，不会中断对话
3. **路径格式**：使用 `/` 开头的绝对路径，符合 BackendProtocol 规范
4. **异步支持**：同时提供同步和异步 API，适配不同场景

## 扩展点

1. **自定义 Backend**：实现 `BackendProtocol` 即可对接任意存储
2. **压缩历史分析**：从 Backend 读取历史数据进行分析
3. **跨会话检索**：利用 Backend 的 grep/glob 检索历史会话
