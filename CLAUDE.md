# CLAUDE.md

本文档为 Claude Code (claude.ai/code) 提供本仓库的代码编写指南。

## 项目概览

一个类 Claude Code 的迷你 Agent 学习项目，采用整洁架构（Clean Architecture），分为 4 层：Interfaces → Application → Domain → Infrastructure。

## 开发命令

```bash
# 虚拟环境（Windows）
.venv-new/Scripts/activate

# 代码质量检查（提交前必须通过）
make check        # 运行全部检查（lint + format + type + bare-dicts）
make fix          # 自动修复所有可修复的问题
make check-bare-dicts  # 检查裸字典字面量（自定义规则）

# 单独检查
make lint         # Ruff 代码检查
make format       # Ruff 格式检查
make format-fix   # Ruff 格式修复
make type         # MyPy 类型检查

# 测试
make test         # 使用 pytest 运行全部测试
pytest tests/test_specific.py -v  # 运行单个测试文件
pytest tests/ -k "test_name" -v   # 运行匹配模式的测试

# Pre-commit 钩子（必需）
pre-commit install
pre-commit run --all-files

# 运行应用
python main.py    # 在 8001 端口启动 FastAPI 服务器（可通过 PORT 环境变量设置）
```

## 关键规则

**Pre-commit 强制规则（不可绕过）：**
- 所有提交必须通过 pre-commit 检查，**禁止**使用 `--no-verify` 跳过
- 发现问题时，**必须先修复问题，再提交代码**
- 运行 `make fix` 可自动修复大部分问题，剩余问题需手动修复
- 例外情况：**绝对禁止**绕过检查，无例外

```bash
git commit -m "xxx" --no-verify  # ❌ 绝对禁止，永不使用
```

**Pydantic 优先原则：** 所有数据模型必须使用 Pydantic。业务数据禁止使用裸字典。自定义脚本 `scripts/check_bare_dicts.py` 会强制执行此规则。

**代码大小限制：** 函数最多 50 行，类最多 200 行，文件最多 300 行。

## 架构

### 分层结构（依赖方向：向内）

```
backend/
├── interfaces/           # HTTP 路由、WebSocket 处理器、CLI
│   ├── http/app.py      # FastAPI 应用工厂
│   ├── websocket/       # WebSocket 处理器
│   └── agent_runtime_bridge.py
├── application/          # 用例、应用服务、DTO
│   ├── dto/             # 请求/响应 DTO
│   ├── services/        # 应用服务
│   └── engine.py        # 主应用引擎
├── domain/               # 业务逻辑、实体、协议
│   ├── models/          # Pydantic 模型（agent/、dialog/、events/、message/、shared/）
│   ├── repositories/    # 仓库接口（协议）
│   └── services/        # 领域服务
└── infrastructure/       # 技术实现
    ├── runtime/         # Agent 运行时
    │   ├── base/        # 公共基类
    │   ├── simple/      # SimpleRuntime
    │   └── deep/        # DeepAgentRuntime
    ├── event_bus/       # 事件总线实现
    ├── container.py     # 全局依赖容器（单例）
    ├── providers/       # LLM 提供商（litellm）
    └── persistence/     # 数据存储实现
```

### 关键运行时类型

- **SimpleRuntime**: 简单任务的基础 Agent 循环
- **DeepAgentRuntime**: 高级运行时，支持工具执行日志和会话管理

### 事件驱动通信

模块通过 `EventBus`（位于 `infrastructure/event_bus/`）通信。禁止直接的跨模块调用。

## 测试

测试结构镜像 backend 结构：
```
tests/
├── runtime/             # Runtime 专项测试
├── infrastructure/      # 基础设施测试
├── e2e/                 # 端到端测试
└── test_*.py           # 各种集成测试
```

## 配置

- Python 版本要求：3.11+
- 主要依赖：FastAPI、Pydantic v2、LiteLLM、LangGraph
- 端口：`PORT` 环境变量（默认 8001）
- API 密钥：在 `.env` 文件中设置（参见 `.env.example`）

## 常用文件位置

- 容器（单例）：`backend/infrastructure/container.py`
- 运行时工厂：`backend/infrastructure/runtime/runtime_factory.py`
- DTO：`backend/application/dto/requests.py`、`backend/application/dto/responses.py`
- 领域模型：`backend/domain/models/`
- 工具实现：`backend/infrastructure/tools/`
