# 使用 Backend 统一存储的示例

## 为什么使用 Backend 统一存储？

deep-agent 的 Backend 系统提供了统一的存储抽象：
- **一致性**：无论使用哪种 Backend（Filesystem, State, Daytona），API 相同
- **可移植性**：切换 Backend 不需要修改压缩中间件代码
- **持久化**：自动处理 LangGraph checkpoint 和外部存储的同步

## 基础示例

### 1. 使用 FilesystemBackend（开发环境）

```python
from core.agent.runtimes.agents import AgentBuilder
from deepagents.backends import FilesystemBackend
from pathlib import Path

# 创建 Backend
project_root = Path(__file__).resolve().parent
backend = FilesystemBackend(root_dir=str(project_root / "data"))

# 创建 Agent（Backend 自动用于压缩存储）
agent = (
    AgentBuilder()
    .with_model("claude-sonnet-4-6")
    .with_tools(tools)
    .with_backend(backend)
    .with_claude_compression(
        level="standard",
        enable_session_memory=True,  # 启用会话记忆存储
    )
    .build()
)

# 存储位置:
# ./data/compression_history/session_{id}_{timestamp}.json
```

### 2. 使用 StateBackend（LangGraph 状态持久化）

```python
from core.agent.runtimes.agents import AgentBuilder
from deepagents.backends import StateBackend
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

# StateBackend 使用 LangGraph 状态存储
backend = StateBackend

checkpointer = MemorySaver()
store = InMemoryStore()

agent = (
    AgentBuilder()
    .with_model("gpt-4")
    .with_tools(tools)
    .with_backend(backend)
    .with_checkpointer(checkpointer)
    .with_store(store)
    .with_claude_compression(
        level="aggressive",
        enable_session_memory=True,
    )
    .build()
)

# 存储位置:
# LangGraph 状态中的 /compression_history/
# 自动与 checkpoint 同步
```

### 3. 使用 Daytona Sandbox（云端部署）

```python
from core.agent.runtimes.agents import AgentBuilder
from daytona import Daytona
from langchain_daytona import DaytonaSandbox

# 创建 Daytona 沙箱
sandbox = Daytona().create()
backend = DaytonaSandbox(sandbox=sandbox)

agent = (
    AgentBuilder()
    .with_model("claude-sonnet-4-6")
    .with_tools(tools)
    .with_backend(backend)
    .with_claude_compression(
        enable_session_memory=True,
    )
    .build()
)

# 存储位置:
# Daytona 沙箱中的 /compression_history/
```

## 高级用法

### 手动保存压缩历史

```python
from core.agent.runtimes.agents.middleware import ClaudeCompressionMiddleware

# 创建中间件
middleware = ClaudeCompressionMiddleware.preset_standard()

# 在会话结束时手动保存历史
async def on_session_end(agent_state, backend, session_id):
    file_path = await middleware.asave_compression_history(
        backend=backend,
        session_id=session_id,
        state=agent_state,
    )
    print(f"Compression history saved: {file_path}")
```

### 读取压缩历史

```python
# 使用 Backend 读取压缩历史
responses = backend.download_files([
    "/compression_history/session_123_history.json"
])

if responses and responses[0].content:
    import json
    history = json.loads(responses[0].content.decode('utf-8'))
    print(f"Total compactions: {history['stats']['total_compactions']}")
    print(f"Tokens saved: {history['stats']['total_tokens_saved']}")
```

### 列出所有会话历史

```python
# 使用 Backend 列出文件
files = backend.ls_info("/compression_history")

for file_info in files:
    print(f"File: {file_info['path']}")
    if 'modified_at' in file_info:
        print(f"Modified: {file_info['modified_at']}")
```

## 不同场景的 Backend 选择

| 场景 | 推荐 Backend | 理由 |
|------|-------------|------|
| 本地开发 | FilesystemBackend | 简单、可见、易调试 |
| 单机部署 | FilesystemBackend + Docker Volume | 持久化到宿主机 |
| Kubernetes | StateBackend + Redis | 分布式状态共享 |
| Serverless | StateBackend + Database | 无状态服务 |
| 云端沙箱 | DaytonaSandbox | 隔离、安全、弹性 |
| 企业集成 | 自定义 Backend | 对接内部存储 |

## 迁移指南

### 从本地文件迁移到 Backend

**旧代码（直接文件操作）**:
```python
# 不推荐：直接操作文件
import json
with open("session_history.json", "w") as f:
    json.dump(data, f)
```

**新代码（使用 Backend）**:
```python
# 推荐：使用 Backend API
result = backend.write("/compression_history/session.json", json.dumps(data))
if result.error:
    logger.error(f"Failed to save: {result.error}")
```

### 从 SummarizationMiddleware 迁移

**deep-agent 原生的压缩**:
```python
from deepagents.middleware.summarization import create_summarization_middleware

summarization = create_summarization_middleware(model, backend)
middleware = [summarization]
```

**新的 Claude Code 压缩**:
```python
from core.agent.runtimes.agents.middleware import ClaudeCompressionMiddleware

compression = ClaudeCompressionMiddleware(
    enable_micro_compact=True,  # 额外：微压缩
    enable_auto_compact=True,   # 对应：原生的自动压缩
)
middleware = [compression]
```

## 调试技巧

### 查看 Backend 存储内容

```python
# 读取会话历史
response = backend.read("/compression_history/session_xxx.json")
print(response)

# 列出所有压缩历史
files = backend.glob_info("*.json", path="/compression_history")
for f in files:
    print(f"{f['path']} - {f.get('size', 0)} bytes")
```

### 验证 Backend 配置

```python
# 检查 Backend 是否可用
def check_backend(backend):
    try:
        result = backend.write("/test.txt", "Hello Backend!")
        if result.error:
            print(f"Backend error: {result.error}")
            return False

        responses = backend.download_files(["/test.txt"])
        if responses[0].content:
            print("Backend is working!")
            return True
    except Exception as e:
        print(f"Backend check failed: {e}")
        return False
```

## 最佳实践

1. **始终传递 Backend**: 在创建 Agent 时显式传递 Backend，确保压缩中间件可以使用存储
2. **处理存储失败**: Backend 写入失败不会中断对话，但会记录 warning
3. **定期清理历史**: 使用 Backend 的接口定期清理旧的压缩历史
4. **监控存储使用**: 通过 Backend 接口监控 /compression_history/ 的存储使用情况
