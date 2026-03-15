# Agent 架构文档

本目录包含 Agent 系统的架构设计文档。

## 文档索引

| 文档 | 说明 |
|------|------|
| [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) | 完整项目结构说明 |
| [refactor-summary.md](../refactor-summary.md) | 重构总结 |
| [backend-state-management-design.md](../backend-state-management-design.md) | 后端状态管理设计 |
| [frontend-pure-rendering-design.md](../frontend-pure-rendering-design.md) | 前端纯渲染设计 |

## 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                          前端层 (Next.js/React)                   │
│         useMessageStore / useWebSocket / EmbeddedDialog          │
└────────────────────────────────┬────────────────────────────────┘
                                 │ WebSocket / HTTP
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI API 层                            │
│                     api/main_new.py                              │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    StateManagedAgentBridge                       │
│              后端状态管理 - 唯一真实数据源                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  DialogStore - 对话框状态管理                             │  │
│  │  - create_dialog()                                       │  │
│  │  - get_bridge()                                          │  │
│  │  - list_dialogs()                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CompositeHooks - Hook 组合                              │  │
│  │  - TodoManagerHook                                       │  │
│  │  - ContextCompactHook                                    │  │
│  │  - MonitoringBridge                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────┘
                                 │ 组合
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SFullAgent                                │
│              agent/s_full.py - 通用智能体                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  BaseAgentLoop - 核心对话循环                             │  │
│  │  - arun() - 异步运行                                       │  │
│  │  - Tool 调用处理                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Skill System - 技能加载                                   │  │
│  │  - core/s05_skill_loading.py                              │  │
│  │  - load_skill()                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 核心特点

### 1. 后端是唯一的真实数据源
- 所有对话状态由 `StateManagedAgentBridge` 维护
- 任何状态变更立即广播快照到前端
- 前端不维护任何对话状态

### 2. 前端纯渲染
- 只接收 `dialog:snapshot` 事件
- 无状态管理逻辑
- 完全依赖后端推送的状态

### 3. Hook 系统
- `CompositeHooks` 组合多个 Hook
- `TodoManagerHook` - 任务管理
- `ContextCompactHook` - 上下文压缩
- 预留 `SqlValidHook` (暂未使用)

### 4. 通用智能体
- 已移除 SQL 特定逻辑
- 通过 Skill 系统支持各种任务
- 可动态加载技能

## 启动方式

```bash
# 后端
cd agents
python start_server.py

# 前端
cd web
npm run dev
```

## 相关代码

- `agents/api/main_new.py` - FastAPI 主应用
- `agents/agent/s_full.py` - 主 Agent 实现
- `agents/hooks/state_managed_agent_bridge.py` - 状态管理
- `agents/models/dialog_types.py` - 数据模型
- `agents/core/s05_skill_loading.py` - Skill 系统
