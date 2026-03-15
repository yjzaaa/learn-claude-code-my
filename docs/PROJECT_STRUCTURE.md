# 项目结构文档

## 目录概览

```
learn-claude-code-my/
├── agents/                 # Python Agent 核心代码
├── docs/                   # 文档
├── history/                # 对话历史记录
├── openspec/               # OpenSpec 变更管理
├── skills/                 # 技能定义
├── study/                  # 学习教程 (s01-s12)
├── tests/                  # 测试文件
├── web/                    # Next.js 前端
└── workspace/              # 工作区
```

## Agents 目录结构

```
agents/
├── __init__.py                    # 包初始化，配置日志
├── start_server.py               # FastAPI 服务器启动脚本
│
├── agent/                        # Agent 实现
│   ├── __init__.py
│   ├── s_full.py                 # 主 Agent (SFullAgent)
│   └── s02_with_skill_loader.py  # Skill Loader Agent
│
├── api/                          # FastAPI API
│   ├── __init__.py
│   └── main_new.py               # API 主入口
│
├── base/                         # 基础类
│   ├── __init__.py
│   ├── base_agent_loop.py        # Agent 循环基类
│   ├── basetool.py               # 工具基类
│   ├── plugin_enabled_agent.py   # 插件化 Agent
│   ├── toolkit.py                # 工具集
│   └── abstract/                 # 抽象接口
│       ├── __init__.py
│       └── hooks.py              # Hook 接口定义
│
├── core/                         # 核心功能
│   ├── __init__.py
│   ├── messages.py               # 消息处理
│   └── s05_skill_loading.py      # Skill 加载系统
│
├── hooks/                        # Hook 实现
│   ├── __init__.py
│   ├── agent_websocket_bridge.py # WebSocket 桥接
│   ├── context_compact_hook.py   # 上下文压缩
│   ├── session_history_hook.py   # 会话历史
│   ├── sql_valid_hook.py         # SQL 验证 (保留但未使用)
│   ├── state_managed_agent_bridge.py  # 状态管理桥接
│   ├── todo_manager_hook.py      # Todo 管理
│   └── composite/                # 组合 Hook
│       ├── __init__.py
│       └── composite_hooks.py
│
├── models/                       # 数据模型
│   ├── __init__.py
│   ├── dialog_types.py           # 对话类型定义
│   └── openai_types.py           # OpenAI 兼容类型
│
├── monitoring/                   # 监控系统
│   ├── __init__.py
│   ├── bridge/                   # 监控桥接
│   ├── domain/                   # 领域模型
│   ├── services/                 # 服务
│   ├── end_to_end_demo.py
│   ├── integrations.py
│   └── websocket_adapter.py
│
├── plugins/                      # 插件系统
│   ├── __init__.py
│   ├── compact_plugin.py
│   └── skill_plugin.py
│
├── providers/                    # LLM 提供商
│   ├── __init__.py
│   ├── base.py
│   ├── litellm_provider.py       # LiteLLM 集成
│   ├── registry.py
│   ├── tool_parser.py
│   └── transcription.py
│
├── session/                      # 会话管理
│   ├── __init__.py
│   ├── history_utils.py          # 历史工具
│   ├── runtime_context.py        # 运行时上下文
│   ├── session_manager.py        # 会话管理器
│   ├── skill_edit_hitl.py        # Skill 编辑 HITL
│   └── todo_hitl.py              # Todo HITL
│
├── utils/                        # 工具函数
│   ├── __init__.py
│   ├── agent_helpers.py          # Agent 辅助函数
│   ├── hook_logger.py            # Hook 日志
│   ├── logging_config.py         # 日志配置
│   ├── workspace_cleanup.py      # 工作区清理
│   └── helpers/                  # 辅助模块
│       ├── __init__.py
│       └── todo_tools.py         # Todo 工具注入
│
└── websocket/                    # WebSocket 层
    ├── __init__.py
    ├── bridge.py
    ├── event_manager.py
    └── server.py
```

## 启动方式

### 后端

```bash
# 方式1：使用启动脚本
cd agents
python start_server.py

# 方式2：使用 uvicorn
cd agents
python -m uvicorn api.main_new:app --host 0.0.0.0 --port 8001 --reload
```

### 前端

```bash
cd web
npm run dev
```

## 关键文件说明

| 文件 | 说明 |
|------|------|
| `agents/api/main_new.py` | FastAPI 主应用入口 |
| `agents/agent/s_full.py` | 主 Agent 实现 (SFullAgent) |
| `agents/core/s05_skill_loading.py` | Skill 加载系统 |
| `agents/hooks/state_managed_agent_bridge.py` | 后端状态管理核心 |
| `agents/models/dialog_types.py` | 数据模型定义 |
| `agents/websocket/server.py` | WebSocket 服务器 |

## 数据流

```
用户输入 → API (main_new.py) → StateManagedAgentBridge → SFullAgent
                                      ↓
                              WebSocket Server ← 前端渲染
```

## 架构特点

1. **后端是唯一的真实数据源** - 所有状态在后端维护
2. **前端纯渲染** - 只接收状态快照，无状态管理
3. **Hook 系统** - 通过 CompositeHooks 组合各种功能
4. **通用智能体** - 已移除 SQL 特定逻辑，可处理通用任务
