# 完整 Hanako 架构文档

## 架构概览

基于 **Facade + 依赖注入 + 事件总线** 的 Hanako 风格架构。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Interface Layer (接口层)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                     │
│  │  HTTP API   │  │  WebSocket  │  │    CLI      │                     │
│  │   Routes    │  │   Server    │  │   (未来)    │                     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                     │
│         └─────────────────┴─────────────────┘                           │
│                           │                                             │
│                           ▼                                             │
│  interfaces/ (纯协议转换，无业务逻辑)                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Core Layer (核心层)                            │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                     AgentEngine (Facade)                         │   │
│   │                      core/engine.py                              │   │
│   │                                                                  │   │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │   │
│   │  │  Dialog  │ │   Tool   │ │  Memory  │ │   Skill  │ │ State  │ │   │
│   │  │ Manager  │ │ Manager  │ │ Manager  │ │ Manager  │ │ Manager│ │   │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │   │
│   │  ┌──────────┐ ┌──────────┐                                       │   │
│   │  │ Provider │ │  (more)  │                                       │   │
│   │  │ Manager  │ │          │                                       │   │
│   │  └──────────┘ └──────────┘                                       │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   core/ (所有 Manager 通过依赖注入获取依赖，不直接引用 Engine)              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Runtime Layer (运行时层)                          │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                        EventBus (事件总线)                       │   │
│   │                     runtime/event_bus.py                         │   │
│   │                                                                  │   │
│   │  事件类型:                                                        │   │
│   │  - DialogCreated, MessageReceived, StreamDelta                   │   │
│   │  - MessageCompleted, ToolCallStarted, ToolCallCompleted          │   │
│   │  - SystemStarted, SystemStopped, ErrorOccurred                   │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   runtime/ (解耦 Core 和 Interface，异步事件驱动)                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
learn-claude-code-my/
├── core/                              # 核心层
│   ├── __init__.py
│   ├── engine.py                      # AgentEngine (Facade)
│   ├── types/                         # 基础类型
│   │   └── __init__.py
│   ├── agent/                         # Agent 抽象
│   │   ├── interface.py               # AgentInterface
│   │   ├── factory.py                 # AgentFactory
│   │   └── simple/                    # SimpleAgent 实现
│   ├── managers/                      # 管理器
│   │   ├── dialog_manager.py          # 对话管理
│   │   ├── tool_manager.py            # 工具管理
│   │   ├── memory_manager.py          # 记忆管理
│   │   ├── skill_manager.py           # 技能管理
│   │   ├── state_manager.py           # 状态管理
│   │   └── provider_manager.py        # Provider 管理
│   ├── models/                        # 领域模型
│   │   ├── dialog.py                  # Dialog, Message, ToolCall
│   │   ├── events.py                  # BaseEvent, 各种事件
│   │   ├── skill.py                   # Skill 模型
│   │   └── artifact.py                # Artifact 模型
│   ├── tools/                         # 工具系统
│   ├── providers/                     # Provider 层
│   └── stores/                        # 数据存储 (预留)
├── runtime/                           # 运行时层
│   ├── __init__.py
│   ├── event_bus.py                   # 事件总线
│   └── events/                        # 事件定义
├── interfaces/                        # 接口层
│   ├── http/                          # HTTP API
│   │   ├── server.py                  # FastAPI 应用
│   │   └── routes/                    # 路由
│   │       ├── health.py
│   │       ├── dialog.py
│   │       ├── skills.py
│   │       └── tools.py
│   └── websocket/                     # WebSocket
│       └── server.py                  # WebSocket 服务器
└── infrastructure/                    # 基础设施 (预留)
```

---

## 核心概念

### 1. AgentEngine (Facade)

统一入口，封装所有内部复杂性。

```python
from core.engine import AgentEngine

engine = AgentEngine(config)
await engine.startup()

# 创建对话
dialog_id = await engine.create_dialog("Hello")

# 发送消息
async for chunk in engine.send_message(dialog_id, "How are you?"):
    print(chunk)

await engine.shutdown()
```

### 2. Managers

每个 Manager 负责一个领域，通过构造函数注入依赖。

| Manager | 职责 |
|---------|------|
| DialogManager | 对话生命周期、消息管理 |
| ToolManager | 工具注册和执行 |
| MemoryManager | 短期/长期记忆、摘要 |
| SkillManager | 技能加载和管理 |
| StateManager | 全局状态、配置 |
| ProviderManager | LLM Provider 管理 |

### 3. EventBus

发布订阅模式，彻底解耦模块。

```python
from runtime.event_bus import EventBus
from runtime.events import DialogCreated

# 订阅事件
unsub = event_bus.subscribe(
    callback=on_dialog_created,
    event_types=['DialogCreated'],
    dialog_id='dlg_xxx'  # 可选: 只订阅特定对话
)

# 发射事件
event_bus.emit(DialogCreated(dialog_id='dlg_xxx', user_input='hello'))
```

### 4. 事件类型

| 事件 | 说明 |
|------|------|
| DialogCreated | 对话创建 |
| MessageReceived | 收到用户消息 |
| StreamDelta | 流式输出增量 |
| MessageCompleted | 消息完成 |
| ToolCallStarted | 工具调用开始 |
| ToolCallCompleted | 工具调用完成 |
| SystemStarted | 系统启动 |
| SystemStopped | 系统停止 |

---

## 使用方式

### 方式 1: 简单 Agent (原有 API)

```python
from core import AgentFactory

agent = AgentFactory.create("simple", "my_agent")
await agent.initialize({"model": "deepseek-chat"})
async for event in agent.run("Hello"):
    print(event)
```

### 方式 2: 完整 Hanako 架构 (推荐)

```python
from core.engine import AgentEngine

# 创建引擎
engine = AgentEngine(config)

# 设置工具
engine.setup_workspace_tools(Path.cwd())

# 启动
await engine.startup()

# 订阅事件
engine.subscribe(on_event, event_types=['DialogCreated'])

# 创建对话
dialog_id = await engine.create_dialog("Hello")

# 发送消息
async for chunk in engine.send_message(dialog_id, "How are you?"):
    print(chunk)

# 关闭
await engine.shutdown()
```

### 方式 3: HTTP API

```python
from core.engine import AgentEngine
from interfaces.http.server import create_app
import uvicorn

engine = AgentEngine(config)
await engine.startup()

app = create_app(engine)
uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 架构优势

| 方面 | 重构前 | 重构后 (Hanako-style) |
|------|--------|----------------------|
| **架构模式** | Hook 系统，深度耦合 | Facade + Manager + EventBus |
| **模块通信** | 直接调用，回调嵌套 | 发布订阅，彻底解耦 |
| **依赖管理** | 循环导入，全局状态 | 构造函数注入 |
| **接口层** | 业务逻辑混杂在路由 | 纯协议转换 |
| **可测试性** | 困难 | 容易 (可 mock) |
| **扩展性** | 困难 | 容易 (添加 Manager) |

---

## 迁移路径

1. **Phase 0** (✅ 完成): 基础架构 (core/)
2. **Phase 1** (✅ 完成): 添加 Managers 和 EventBus
3. **Phase 2** (✅ 完成): 添加 Interface 层
4. **Phase 3** (未来): 迁移旧代码使用新架构
5. **Phase 4** (未来): 添加更多功能 (Persistence, Monitoring)

---

## 文件清单

### 核心文件 (已完成)

```
core/
├── engine.py              # Facade
core/managers/
├── dialog_manager.py      # 对话管理
├── tool_manager.py        # 工具管理
├── memory_manager.py      # 记忆管理
├── skill_manager.py       # 技能管理
├── state_manager.py       # 状态管理
└── provider_manager.py    # Provider 管理
runtime/
├── event_bus.py           # 事件总线
interfaces/
├── http/
│   ├── server.py          # FastAPI 应用
│   └── routes/            # 路由
└── websocket/
    └── server.py          # WebSocket 服务器
```

---

*文档版本: 1.0*
*更新日期: 2026-03-20*
