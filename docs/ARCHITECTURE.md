# Agent 新架构说明

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent 五层架构 (v3.0)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Layer 1: interfaces/          接口层                                │   │
│  │  ┌──────────────┐  ┌──────────────┐                                  │   │
│  │  │   HTTP API   │  │  WebSocket   │  ← 对外暴露的服务端点              │   │
│  │  │  (RESTful)   │  │  (Realtime)  │                                  │   │
│  │  └──────────────┘  └──────────────┘                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Layer 2: runtime/             运行时层                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │AgentBuilder  │  │ EventSystem  │  │StateManager  │  ← 协调核心    │   │
│  │  │  (构建器)    │  │  (事件系统)  │  │  (状态管理)  │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Layer 3: kernel/              内核层                                │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                    KernelAgent (单一核心类)                   │   │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │   │   │
│  │  │  │PluginRegistry│  │   arun()     │  │   run()      │       │   │   │
│  │  │  │  (插件注册)  │  │ (异步运行)   │  │ (同步运行)   │       │   │   │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘       │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Layer 4: plugins/             插件层                                │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │   todo   │ │   task   │ │ background│ │ subagent │ │   team   │  │   │
│  │  │  (待办)  │ │ (持久化) │ │  (后台)  │ │ (子代理) │ │ (团队)   │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  │  ┌──────────┐ ┌──────────┐                                         │   │
│  │  │   plan   │ │   skill  │  ← 功能扩展插件                         │   │
│  │  │ (审批)   │ │ (技能)   │                                         │   │
│  │  └──────────┘ └──────────┘                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Layer 5: infrastructure/      基础设施层                            │   │
│  │  ┌────────────────────────┐  ┌────────────────────────┐            │   │
│  │  │        llm/            │  │        tools/          │  ← 底层能力 │   │
│  │  │  ┌──────────────────┐  │  │  ┌──────────────────┐  │            │   │
│  │  │  │ LLMProvider      │  │  │  │ @tool decorator  │  │            │   │
│  │  │  │ LiteLLMProvider  │  │  │  │ bash, edit, read │  │            │   │
│  │  │  └──────────────────┘  │  │  └──────────────────┘  │            │   │
│  │  └────────────────────────┘  └────────────────────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 数据流向图

```
┌─────────────┐     HTTP/WS      ┌─────────────────────────────────────────┐
│   Client    │◄───────────────►│           interfaces/                   │
│  (Web/App)  │                  │  ┌─────────────┐    ┌─────────────┐    │
└─────────────┘                  │  │  HTTP API   │    │  WebSocket  │    │
                                 │  └──────┬──────┘    └──────┬──────┘    │
                                 └─────────┼────────────────┼─────────────┘
                                           │                │
                                           ▼                ▼
                                 ┌─────────────────────────────────────────┐
                                 │           runtime/                      │
                                 │  ┌─────────────┐    ┌─────────────┐    │
                    ┌───────────►│  │EventSystem  │◄───│StateManager │    │
                    │            │  └──────┬──────┘    └─────────────┘    │
                    │            └─────────┼───────────────────────────────┘
                    │                      │
         Broadcast  │                      ▼  Emit Events
         Events     │            ┌─────────────────────────────────────────┐
                    │            │           kernel/                       │
                    │            │        ┌─────────────┐                  │
                    │            │        │ KernelAgent │                  │
                    │            │        └──────┬──────┘                  │
                    │            └─────────────────┼───────────────────────┘
                    │                              │
                    │                              ▼ Load Plugins
                    │            ┌─────────────────────────────────────────┐
                    │            │           plugins/                      │
                    │            │  ┌──────────┐ ┌──────────┐ ┌────────┐  │
                    │            │  │  todo    │ │  task    │ │  ...   │  │
                    │            │  └──────────┘ └──────────┘ └────────┘  │
                    │            └─────────────────┬───────────────────────┘
                    │                              │
                    │                              ▼ Call Tools
                    │            ┌─────────────────────────────────────────┐
                    │            │        infrastructure/                  │
                    │            │  ┌──────────┐      ┌─────────────────┐  │
                    └────────────┤  │   LLM    │      │     Tools       │  │
                                 │  │  (chat)  │      │ (bash, edit...) │  │
                                 │  └──────────┘      └─────────────────┘  │
                                 └─────────────────────────────────────────┘
```

## 目录结构

```
agents/
├── interfaces/          # 接口层 - 对外暴露的 API
│   ├── http/           # HTTP REST API
│   │   ├── server.py   # FastAPI 应用
│   │   └── __init__.py
│   └── websocket/      # WebSocket 实时通信
│       ├── server.py   # WebSocket 服务器
│       ├── connection.py # 连接管理
│       └── __init__.py
│
├── runtime/            # 运行时层 - 协调核心
│   ├── events.py       # 统一事件系统
│   ├── state.py        # 集中状态管理
│   ├── builder.py      # Agent 构建器
│   └── __init__.py
│
├── kernel/             # 内核层 - 最小核心
│   ├── agent.py        # KernelAgent (单一核心类)
│   ├── plugin.py       # 插件基类接口
│   ├── registry.py     # 插件注册表
│   └── __init__.py
│
├── plugins/            # 插件层 - 功能扩展
│   ├── __init__.py
│   └── builtin/        # 内置插件
│       ├── todo/       # 待办事项插件
│       ├── task/       # 持久化任务插件
│       ├── background/ # 后台执行插件
│       ├── subagent/   # 子代理插件
│       ├── team/       # 团队协作插件
│       ├── plan/       # 计划审批插件
│       └── skill/      # 技能加载插件
│
├── infrastructure/     # 基础设施层 - 底层能力
│   ├── llm/            # LLM 提供者
│   │   ├── base.py     # 基础接口
│   │   └── litellm.py  # LiteLLM 实现
│   └── tools/          # 工具基础设施
│       ├── base.py     # 工具装饰器
│       ├── bash.py     # Bash 工具
│       └── filesystem.py # 文件工具
│
├── models/             # Pydantic 数据模型
├── utils/              # 工具函数
└── tests/              # 测试目录
```

## 架构原则

### 1. 单向依赖
```
interfaces/ → runtime/ → kernel/ → plugins/, infrastructure/
```
- 上层可以依赖下层
- 下层不能依赖上层
- 同层之间通过 kernel/ 协调

### 2. 单一核心类
- `KernelAgent` 是唯一的 Agent 核心类
- 所有功能通过插件扩展
- 插件实现 `BasePlugin` 接口

### 3. 统一事件系统
- `EventSystem` 合并了原有的 hooks + monitoring
- 支持同步处理器和异步外部适配器
- WebSocket 通过 `ExternalAdapter` 接口集成

### 4. 集中状态管理
- `StateManager` 提供统一的状态存储
- 插件通过 `plugin(name)` 获取隔离的状态空间
- 状态持久化和同步由运行时层处理

## 快速开始

### 启动服务器

```bash
# 新架构服务器
python -m agents.server

# 指定端口
python -m agents.server --port 8000

# 热重载模式
python -m agents.server --reload
```

### 使用 AgentBuilder

```python
from agents import AgentBuilder
from agents.plugins.builtin.todo import TodoPlugin
from agents.plugins.builtin.background import BackgroundPlugin

# 构建 Agent
agent = (
    AgentBuilder()
    .with_provider(create_provider_from_env())
    .with_base_tools()
    .with_plugin(TodoPlugin())
    .with_plugin(BackgroundPlugin(max_workers=4))
    .build()
)

# 运行
result = await agent.arun([
    {"role": "user", "content": "Hello"}
])
```

### 创建自定义插件

```python
from agents.kernel.plugin import BasePlugin
from agents.infrastructure.tools import tool

class MyPlugin(BasePlugin):
    name = "my_plugin"

    def on_load(self, agent):
        # 插件加载时调用
        self.agent = agent
        self.state = agent.state.plugin(self.name)

    def get_tools(self):
        # 返回插件提供的工具
        return [self.my_tool]

    @tool(description="My custom tool")
    def my_tool(self, arg: str) -> str:
        return f"Result: {arg}"

    def on_unload(self):
        # 插件卸载时调用
        pass
```

## API 端点

### HTTP API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 服务信息 |
| GET | `/health` | 健康检查 |
| GET | `/api/dialogs` | 列出所有对话 |
| POST | `/api/dialogs` | 创建新对话 |
| GET | `/api/dialogs/{id}` | 获取对话详情 |
| POST | `/api/dialogs/{id}/messages` | 发送消息 |
| POST | `/api/dialogs/{id}/stop` | 停止对话 |

### WebSocket

连接: `ws://localhost:8001/ws/{dialog_id}`

客户端事件:
- `subscribe` - 订阅对话
- `user:input` - 用户输入
- `stop` - 停止 Agent

服务器事件:
- `connection.established` - 连接成功
- `subscription.confirmed` - 订阅确认
- `dialog.snapshot` - 对话状态快照

## 从旧架构迁移

### 1. 替换导入
```python
# 旧
from agents.agent.s_full import SFullAgent
from agents.hooks.state_managed_agent_bridge import StateManagedAgentBridge

# 新
from agents import AgentBuilder
from agents.runtime import EventSystem, StateManager
```

### 2. 创建 Agent
```python
# 旧
agent = SFullAgent(provider=provider)

# 新
agent = (
    AgentBuilder()
    .with_provider(provider)
    .with_base_tools()
    .build()
)
```

### 3. 事件处理
```python
# 旧 - hooks
hook.on_tool_call(name, arguments, tool_call_id)

# 新 - EventSystem
event_system.emit(EventType.TOOL_CALL, {
    "name": name,
    "arguments": arguments,
    "tool_call_id": tool_call_id
})
```
