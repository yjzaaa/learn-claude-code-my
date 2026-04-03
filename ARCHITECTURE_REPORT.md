# Hana Agent 项目架构报告

## 项目概述

**项目名称**: learn-claude-code-my / Hana Agent
**技术栈**: FastAPI (Python) + Next.js 16 (React 19 + TypeScript)
**定位**: 类 Claude Code 的 Agent 学习项目，实现完整的前后端 Agent 系统

---

## 目录结构

```
D:\learn-claude-code-my/
├── main.py                    # FastAPI 入口点
├── requirements.txt           # Python 依赖
├── pyproject.toml            # 项目配置
├── core/                     # 后端核心代码
│   ├── engine.py            # AgentEngine 门面
│   ├── agent/               # Agent 运行时架构
│   ├── managers/            # 六大管理器
│   ├── models/              # Pydantic 模型 + TypedDict
│   ├── providers/           # LLM Provider
│   ├── tools/               # 工具注册和执行
│   ├── plugins/             # 插件系统
│   ├── hitl/                # Human-in-the-loop
│   ├── runtime/             # 运行时基础设施
│   ├── bridge/              # 桥接接口
│   ├── capabilities/        # 能力接口
│   ├── container.py         # 依赖注入容器
│   └── types/               # 类型定义
├── interfaces/              # 接口层
│   ├── http/               # HTTP 路由
│   └── websocket/          # WebSocket 处理
├── runtime/                # 运行时配置
│   ├── event_bus.py       # 事件总线
│   └── logging_config.py  # 日志配置
├── skills/                 # Skill 目录
├── web/                    # 前端 (Next.js)
│   ├── src/
│   │   ├── app/           # Next.js App Router
│   │   ├── components/    # React 组件
│   │   ├── hooks/         # React Hooks
│   │   ├── lib/           # 工具库
│   │   ├── stores/        # Zustand 状态管理
│   │   └── types/         # TypeScript 类型
│   └── package.json
└── tests/                  # 测试目录
```

---

## 后端架构详解

### 1. 入口层 (main.py)

**职责**: FastAPI 应用 + WebSocket 服务器

**核心组件**:
- `AgentEngine` 单例实例
- WebSocket 客户端集合 `_ws_clients`
- 状态追踪 (`_status`, `_streaming_msg`)
- 后台 Agent 运行器 `_run_agent()`

**关键端点**:
```
GET    /health                    # 健康检查
GET    /api/dialogs              # 列出对话
POST   /api/dialogs              # 创建对话
GET    /api/dialogs/{id}         # 获取对话
DELETE /api/dialogs/{id}         # 删除对话
POST   /api/dialogs/{id}/messages # 发送消息
POST   /api/dialogs/{id}/resume  # 恢复对话
GET    /api/agent/status         # Agent 状态
POST   /api/agent/stop           # 停止 Agent
GET    /api/skills               # 列出技能
WS     /ws/{client_id}           # WebSocket 连接
```

### 2. 核心引擎 (core/engine.py)

**设计模式**: Facade (门面模式)

**六大管理器**:
| 管理器 | 文件 | 职责 |
|--------|------|------|
| StateManager | `core/managers/state_manager.py` | 状态管理 |
| ProviderManager | `core/managers/provider_manager.py` | LLM Provider |
| DialogManager | `core/managers/dialog_manager.py` | 对话 CRUD |
| ToolManager | `core/managers/tool_manager.py` | 工具注册执行 |
| MemoryManager | `core/managers/memory_manager.py` | 上下文/记忆 |
| SkillManager | `core/managers/skill_manager.py` | Skill 动态加载 |

**事件驱动**: 所有管理器通过 `runtime/event_bus.py` 通信

### 3. Agent Runtime 架构 (core/agent/)

**抽象基类** (`core/agent/runtime.py`):
```python
class AgentRuntime(ABC):
    @abstractmethod
    async def send_message(...) -> AsyncIterator[AgentEvent]: ...
    @abstractmethod
    async def create_dialog(...) -> str: ...
    @abstractmethod
    def register_tool(...) -> None: ...
```

**工厂模式** (`core/agent/factory.py`):
```python
class AgentFactory:
    _registry = {
        "simple": SimpleAgent,
        # "langgraph": LangGraphAgent,  # 未来
    }
    @classmethod
    def create(agent_type: str, agent_id: str) -> AgentInterface
```

**运行时实现**:
- `simple/agent.py` - 原生轻量级实现
- `runtimes/simple_runtime.py` - SimpleRuntime
- `runtimes/deep_runtime.py` - DeepAgentRuntime (基于 deep-agents 框架)

### 4. 数据模型层 (core/models/)

**模型分类**:
| 文件 | 内容 |
|------|------|
| `types.py` | TypedDict 类型定义 |
| `config.py` | EngineConfig 等配置模型 |
| `dialog.py` | Dialog, Message 对话模型 |
| `domain.py` | Skill, 领域实体 |
| `events.py` | SystemStarted, ErrorOccurred 等事件 |
| `dto.py` | DecisionResult, TodoStateDTO 等 DTO |
| `tool.py` | ToolInfo 工具信息 |

**类型安全**: 使用 Pydantic BaseModel + TypedDict，禁止裸 dict

### 5. Provider 层 (core/providers/)

**抽象基类** (`base.py`):
```python
class BaseProvider(ABC):
    @abstractmethod
    async def chat_completion(...) -> AsyncIterator[StreamChunk]: ...
```

**实现**:
- `litellm_provider.py` - 基于 LiteLLM 的多供应商支持

**支持供应商**:
- Anthropic (Claude)
- DeepSeek
- Moonshot (Kimi)
- Zhipu (GLM)
- MiniMax

### 6. 工具系统 (core/tools/)

**组件**:
- `registry.py` - 工具注册表
- `toolkit.py` - 工具装饰器 (`@tool`)
- `workspace.py` - 工作区操作

### 7. 插件系统 (core/plugins/)

**组件**:
- `base.py` - 插件基类
- `compact_plugin.py` - 上下文窗口压缩插件

### 8. HITL (Human-in-the-Loop) (core/hitl/)

**组件**:
- `todo.py` - Todo 列表管理
- `skill_edit.py` - Skill 编辑流程

---

## 前端架构详解

### 1. 技术栈

- **框架**: Next.js 16 (App Router)
- **React**: React 19
- **语言**: TypeScript
- **样式**: Tailwind CSS
- **状态**: Zustand
- **事件**: EventEmitter3

### 2. 目录结构

```
web/src/
├── app/
│   ├── [locale]/              # i18n 路由
│   │   ├── chat/              # 聊天页面
│   │   ├── agent/             # Agent 页面
│   │   ├── settings/          # 设置页面
│   │   └── (learn)/           # 学习页面
│   └── page.tsx               # 首页
├── components/
│   ├── chat/                  # 聊天组件
│   │   ├── ChatShell.tsx
│   │   ├── ChatArea.tsx
│   │   ├── MessageItem.tsx
│   │   ├── InputArea.tsx
│   │   └── SessionSidebar.tsx
│   ├── layout/                # 布局组件
│   └── monitoring/            # 监控组件
├── hooks/
│   ├── useMessageStore.ts     # 消息状态管理
│   ├── useWebSocket.ts        # WebSocket 连接
│   └── useAgentApi.ts         # Agent API 调用
├── lib/
│   └── event-emitter.ts       # 全局事件发射器
├── stores/                    # Zustand Store
└── types/                     # TypeScript 类型
```

### 3. 状态管理 (Zustand)

**useMessageStore** (`hooks/useMessageStore.ts`):
```typescript
interface MessageStoreState {
  dialogs: ChatSession[];
  currentDialog: ChatSession | null;
  isLoading: boolean;
  error: string | null;
  streamState: AgentStreamState;
}
```

### 4. WebSocket 通信

**流程**:
1. 建立 WebSocket 连接 (`useWebSocket.ts`)
2. 订阅对话 (`subscribe` 消息)
3. 接收流式事件:
   - `dialog:snapshot` - 完整对话状态
   - `stream:delta` - 流式内容片段
   - `status:change` - 状态变化
   - `error` - 错误信息

---

## 数据流

### 1. 消息发送流程

```
用户输入
  ↓
[前端] InputArea.onSubmit
  ↓
[前端] useAgentApi.sendMessage (POST /api/dialogs/{id}/messages)
  ↓
[后端] main.py:send_message
  ↓
[后端] asyncio.create_task(_run_agent) ← 后台任务
  ↓
[后端] engine.send_message() → AgentEngine
  ↓
[后端] AgentEngine 处理 → 流式响应
  ↓
[后端] _broadcast() → WebSocket 广播
  ↓
[前端] useWebSocket.onMessage
  ↓
[前端] useMessageStore 更新状态
  ↓
[前端] ChatArea 重新渲染
```

### 2. 事件总线通信

```
Manager A
  ↓ publish(event)
[runtime/event_bus.py]
  ↓
Manager B (subscriber)
```

---

## 配置说明

### 环境变量 (.env)

```bash
# 必需
ANTHROPIC_API_KEY=sk-ant-xxx
MODEL_ID=claude-sonnet-4-6

# Agent Runtime 类型
AGENT_TYPE=simple  # 或 deep
MAX_AGENT_ROUNDS=10

# 工具白名单
BASH_SCRIPT_WHITELIST=.workspace;skills/**/scripts
WRITE_TOOL_WHITELIST=.workspace
READ_TOOL_BLACKLIST=.env

# 日志
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
LOG_ROTATION=10 MB
LOG_RETENTION=7 days
```

---

## 代码规范

### Python
- 使用 Pydantic BaseModel，禁止裸 dict
- 文件不超过 300 行
- 函数不超过 50 行
- 类不超过 200 行
- 异步函数必须使用 async/await

### TypeScript
- 优先使用 interface 而非 type
- 严格模式，禁用 any
- React Hooks 不在循环/条件中调用

---

## 启动流程

### 后端
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env
# 编辑 .env 添加 API key

# 3. 启动服务
python main.py  # 默认端口 8001
```

### 前端
```bash
cd web
npm install
npm run dev  # http://localhost:3000
```

---

## 扩展点

### 1. 添加新的 Agent 类型
1. 实现 `AgentInterface` 接口
2. 在 `AgentFactory._registry` 中注册

### 2. 添加新工具
1. 在 `skills/` 下创建 Skill 目录
2. 编写 `SKILL.md` 文档
3. 在 `scripts/` 中使用 `@tool` 装饰器定义工具

### 3. 添加新 Provider
1. 继承 `BaseProvider`
2. 实现 `chat_completion` 方法

---

## 关键设计决策

1. **Facade 模式**: AgentEngine 作为统一入口，隐藏内部复杂性
2. **Manager 模式**: 六大管理器各司其职，通过事件总线解耦
3. **工厂模式**: AgentFactory 支持运行时切换 Agent 实现
4. **前端中心化状态**: 后端不存储对话状态，前端通过 WebSocket 接收实时更新
5. **Pydantic 严格类型**: 全项目使用 Pydantic 模型，保证类型安全

---

## 报告生成时间

生成时间: 2026-03-30
Git Commit: 0c6c860 (refactor: 用 TypedDict 替换全局裸 dict，重构核心架构)
