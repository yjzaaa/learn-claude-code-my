# 架构对比分析

## 两个设计的关系

| 维度 | 我的设计 (`core/`) | 原设计 (`REFACTOR_ARCHITECTURE.md`) |
|------|-------------------|-----------------------------------|
| **目标** | Agent 抽象 + SDK 适配 | 完整系统重构 (Hanako-style) |
| **范围** | Agent 核心 (最小可用) | 整个系统 (完整功能) |
| **复杂度** | 简单 | 完整 |
| **阶段** | Phase 0: 基础抽象 | Phase 1-5: 完整实现 |

---

## 详细对比

### 1. 目录结构

```
我的设计 (已实现 core/)
============================
core/
├── types/           # 基础类型
├── agent/           # Agent 抽象
│   ├── interface.py      # AgentInterface
│   ├── factory.py        # AgentFactory
│   ├── simple/           # SimpleAgent
│   └── adapters/         # SDK 适配器预留
├── tools/           # 工具系统
└── providers/       # Provider 层

原设计 (规划 REFACTOR_ARCHITECTURE.md)
============================
core/
├── engine.py              # AgentEngine (Facade)
├── managers/              # 各种 Manager
├── models/                # 领域模型
└── stores/                # 数据存储

runtime/                   # 运行时层
├── event_bus.py
├── events/
└── stream/

interfaces/                # 接口层
├── http/
└── websocket/

infrastructure/            # 基础设施
```

### 2. 关键差异

| 方面 | 我的设计 | 原设计 | 兼容性 |
|------|---------|--------|--------|
| **Agent 抽象** | `AgentInterface` | `AgentEngine` (Facade) | ✅ 兼容 |
| **事件系统** | `AgentLifecycleHooks` (同步钩子) | `EventBus` (异步发布订阅) | ⚠️ 可扩展 |
| **工具管理** | `ToolRegistry` | `ToolManager` | ✅ 兼容 |
| **对话管理** | 简单 Agent 状态 | `DialogManager` + `MessageStore` | ⚠️ 需扩展 |
| **依赖注入** | 构造函数注入 | 构造函数注入 | ✅ 一致 |

### 3. 关系图

```
原设计 (完整 Hanako-style)
============================
┌─────────────────────────────────────┐
│         Interface Layer              │
│    (HTTP Routes / WebSocket)         │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│           Core Layer                 │
│  ┌───────────────────────────────┐  │
│  │      AgentEngine (Facade)      │  │
│  │  ┌─────┐ ┌─────┐ ┌─────┐     │  │
│  │  │Dialog│ │Tool │ │Skill│ ... │  │
│  │  │Manager│ │Manager│ │Manager│  │  │
│  │  └─────┘ └─────┘ └─────┘     │  │
│  └───────────────────────────────┘  │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Runtime Layer                │
│         (EventBus)                   │
└─────────────────────────────────────┘

我的设计 (简化版)
============================
┌─────────────────────────────────────┐
│    Interface (用户代码/API)          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         AgentFactory                 │
│              │                       │
│    ┌─────────┼─────────┐            │
│    ▼         ▼         ▼            │
│ Simple  LangGraph  CrewAI          │
│ Agent   Adapter    Adapter         │
│    │                                │
│    └──────► ToolRegistry           │
└─────────────────────────────────────┘
```

### 4. 结论

**我的设计是原设计的一个子集：**

1. **核心抽象一致**: 都使用 `AgentInterface` 抽象，预留 SDK 适配
2. **依赖注入一致**: 都通过构造函数注入依赖
3. **层次清晰**: 都遵循分层架构

**原设计是完整实现，我的设计是简化 MVP：**

- 原设计包含完整的 EventBus、Managers、接口层
- 我的设计只包含 Agent 核心，但可独立运行

---

## 建议的整合方案

### 方案 A: 以我的设计为基础，逐步扩展 (推荐)

```
步骤 1: 保留 core/ (我的设计) 作为基础
步骤 2: 添加 core/engine.py (原设计的 Facade)
步骤 3: 逐步添加 managers/ (原设计)
步骤 4: 添加 runtime/event_bus.py (原设计)
步骤 5: 迁移 interfaces/ (原设计)
```

**优势**:
- 已有代码可用 (core/ 已测试通过)
- 渐进式扩展，风险低
- 最终架构与原设计一致

### 方案 B: 直接使用原设计

```
步骤 1: 按照 REFACTOR_ARCHITECTURE.md 创建完整结构
步骤 2: 一次性实现所有组件
步骤 3: 替换旧代码
```

**优势**:
- 架构完整，一步到位

**劣势**:
- 工作量大，风险高
- 需要更长时间才能可用

---

## 推荐行动

**选择方案 A** (渐进式扩展):

1. **现在**: 保留 `core/` 作为基础
2. **下一步**: 添加 `core/engine.py` 作为 Facade
3. **然后**: 添加 `runtime/event_bus.py`
4. **最后**: 完善 managers/

这样既利用了已完成的工作，又朝着原设计演进。

你想：
1. **采用方案 A**: 在现有 core/ 基础上扩展
2. **采用方案 B**: 直接按原设计实现
3. **查看具体差异**: 对比某个具体模块的实现
