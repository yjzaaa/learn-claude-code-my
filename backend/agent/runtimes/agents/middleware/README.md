# Claude Code 压缩中间件

将 Claude Code 的 4 层压缩系统移植到 deep-agent 框架，**统一使用 deep-agent Backend 存储**。

## 特性

- ✅ **4层渐进式压缩**：Micro → Auto → Partial → Session
- ✅ **统一 Backend 存储**：所有持久化操作使用 deep-agent BackendProtocol
- ✅ **多 Backend 支持**：Filesystem、State、DaytonaSandbox 等
- ✅ **完整的统计信息**：详细的压缩事件历史和统计

## 快速开始

```python
from core.agent.runtimes.agents import AgentBuilder
from deepagents.backends import FilesystemBackend

# 创建 Backend
backend = FilesystemBackend(root_dir="./data")

# 创建 Agent
agent = (
    AgentBuilder()
    .with_model("claude-sonnet-4-6")
    .with_backend(backend)  # Backend 自动用于压缩存储
    .with_claude_compression(level="standard")
    .build()
)
```

## 文件结构

```
middleware/
├── __init__.py                      # 模块导出
├── types.py                         # 配置类
├── compression_strategies.py        # 4层压缩策略
├── claude_compression_middleware.py # 主中间件
├── DESIGN.md                        # 架构设计文档
├── EXAMPLES_BACKEND.md              # Backend 使用示例
└── README.md                        # 本文件
```

## 使用方式

### 1. 预设配置

```python
from core.agent.runtimes.agents import AgentBuilder

# 标准压缩（推荐）
agent = (
    AgentBuilder()
    .with_claude_compression(level="standard")
    .build()
)

# 仅微压缩（最低开销）
agent = (
    AgentBuilder()
    .with_micro_compact_only()
    .build()
)

# 激进压缩（最大节省）
agent = (
    AgentBuilder()
    .with_aggressive_compression()
    .build()
)
```

### 2. 自定义配置

```python
agent = (
    AgentBuilder()
    .with_claude_compression(
        level="custom",
        auto_compact_threshold=0.75,
        enable_micro_compact=True,
        enable_auto_compact=True,
        enable_session_memory=True,  # 启用 Backend 存储会话
    )
    .build()
)
```

### 3. 直接使用中间件

```python
from core.agent.runtimes.agents.middleware import ClaudeCompressionMiddleware

# 创建中间件
middleware = ClaudeCompressionMiddleware(
    enable_micro_compact=True,
    enable_auto_compact=True,
    enable_session_memory=True,  # 使用 Backend 存储
)

# 添加到 Agent
agent = (
    AgentBuilder()
    .with_model("gpt-4")
    .add_middleware(middleware)
    .build()
)

# 手动保存压缩历史到 Backend
file_path = middleware.save_compression_history(
    backend=backend,
    session_id="session_123",
    state=agent_state,
)
```

## Backend 存储

### 存储路径

```
/compression_history/
├── session_{session_id}_{timestamp}.json     # 会话历史
├── {session_id}_history.json                  # 压缩事件历史
└── ...
```

### 支持的 Backend

| Backend | 存储位置 |
|---------|---------|
| FilesystemBackend | 本地文件系统 |
| StateBackend | LangGraph 状态 |
| DaytonaSandbox | 远程沙箱 |
| 自定义 Backend | 任意位置 |

## 配置选项

```python
from core.agent.runtimes.agents.middleware import CompressionConfig

config = CompressionConfig(
    enable_micro_compact=True,
    enable_auto_compact=True,
    enable_partial_compact=False,
    enable_session_memory=False,

    session=SessionMemoryConfig(
        storage_path_prefix="/compression_history",  # Backend 存储路径
        enable_cross_session_recovery=True,
        save_to_backend=True,  # 使用 Backend 存储
    ),
)
```

## 与 deep-agent 原生压缩对比

| 特性 | deep-agent SummarizationMiddleware | ClaudeCompressionMiddleware |
|------|-----------------------------------|----------------------------|
| 存储方式 | Backend 存储 | ✅ 相同的 Backend 存储 |
| 压缩层级 | 单层 | ✅ 4层渐进式 |
| 微压缩 | 简单参数截断 | ✅ 工具结果缓存管理 |
| 压缩历史 | 无 | ✅ Backend 存储 |
| 统计信息 | 基础 | ✅ 详细事件历史 |

## 文档

- [DESIGN.md](./DESIGN.md) - 架构设计文档
- [EXAMPLES_BACKEND.md](./EXAMPLES_BACKEND.md) - Backend 使用示例

## 依赖

```python
# 核心依赖
deepagents  # deep-agent 框架
langchain_core
langgraph

# 可选依赖（根据使用的 Backend）
daytona  # 如果使用 DaytonaSandbox
```
