# Backend Architecture - 后端架构文档

## 概述

本项目采用 **Clean Architecture（整洁架构）** 模式，将代码组织为四个清晰的层次，每层有明确的职责边界。

```
┌─────────────────────────────────────────────────────────────┐
│                      Interfaces Layer                       │
│         (HTTP Routes, WebSocket Handlers, CLI)              │
├─────────────────────────────────────────────────────────────┤
│                   Application Layer                         │
│       (Use Cases, Application Services, DTOs)              │
├─────────────────────────────────────────────────────────────┤
│                    Domain Layer                             │
│    (Entities, Value Objects, Domain Events, Protocols)     │
├─────────────────────────────────────────────────────────────┤
│                  Infrastructure Layer                       │
│   (Persistence, External Services, Runtime Implementations)│
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
backend/
├── domain/                    # 领域层 - 核心业务逻辑
│   ├── models/               # 领域模型（按领域组织）
│   │   ├── agent/           # Agent 相关模型
│   │   │   ├── skill.py
│   │   │   ├── tool.py
│   │   │   └── tool_call.py
│   │   ├── api/             # API 相关模型
│   │   ├── dialog/          # 对话相关模型
│   │   │   ├── dialog.py
│   │   │   ├── session.py
│   │   │   └── manager.py
│   │   ├── events/          # 事件模型
│   │   │   ├── base.py
│   │   │   ├── agent.py
│   │   │   └── websocket.py
│   │   ├── message/         # 消息相关模型
│   │   └── shared/          # 共享类型
│   │       ├── base.py
│   │       ├── config.py
│   │       ├── mixins.py
│   │       └── types.py
│   └── repositories/        # 仓库接口（协议）
│       ├── dialog.py
│       └── skill.py
│
├── application/              # 应用层 - 用例和应用服务
│   ├── dto/                 # 数据传输对象
│   │   ├── requests.py
│   │   └── responses.py
│   ├── protocols/           # 应用层协议
│   │   └── capabilities.py
│   └── services/            # 应用服务
│       ├── dialog.py
│       ├── skill.py
│       ├── memory.py
│       └── agent_orchestration.py
│
├── infrastructure/           # 基础设施层 - 技术实现
│   ├── logging/             # 日志配置
│   ├── persistence/         # 持久化实现
│   │   ├── dialog_memory.py
│   │   └── skill_memory.py
│   ├── plugins/             # 插件系统
│   ├── providers/           # LLM Provider 实现
│   │   └── litellm.py
│   ├── protocols/           # 基础设施协议
│   │   ├── provider.py
│   │   └── runtime.py
│   ├── runtime/             # Runtime 实现
│   │   ├── runtime.py
│   │   ├── simple.py
│   │   ├── deep.py
│   │   ├── manager.py
│   │   └── event_bus.py
│   ├── services/            # 基础设施服务
│   │   ├── dialog_manager.py
│   │   ├── skill_manager.py
│   │   └── tool_manager.py
│   └── tools/               # 工具实现
│
└── interfaces/              # 接口层 - 外部交互
    ├── http/                # HTTP API
    │   ├── server.py
    │   └── routes/
    ├── websocket/           # WebSocket
    │   ├── server.py
    │   └── manager.py
    └── agent_runtime_bridge.py
```

## 分层职责

### 1. Domain Layer（领域层）

**职责**：定义核心业务逻辑和业务规则。

**包含**：
- **Entities（实体）**：具有唯一标识的业务对象（如 Dialog, Session, Skill）
- **Value Objects（值对象）**：无标识的不可变对象（如 MessageContent, Config）
- **Domain Events（领域事件）**：业务发生的事情（如 MessageReceived, ToolCallStarted）
- **Repository Protocols（仓库协议）**：数据访问接口定义

**依赖规则**：
- 只依赖 Python 标准库和 Pydantic
- 不依赖其他层（Application, Infrastructure, Interfaces）

### 2. Application Layer（应用层）

**职责**：编排用例，协调领域对象完成业务功能。

**包含**：
- **Application Services（应用服务）**：实现具体用例（如 SendMessageUseCase）
- **DTOs（数据传输对象）**：跨层数据传输
- **Application Protocols（应用协议）**：应用层接口定义

**依赖规则**：
- 只依赖 Domain Layer
- 通过接口（协议）访问 Infrastructure Layer

### 3. Infrastructure Layer（基础设施层）

**职责**：提供技术实现，支持上层需求。

**包含**：
- **Persistence（持久化）**：数据存储实现（如 InMemoryDialogRepository）
- **External Services（外部服务）**：LLM Provider、第三方 API
- **Runtime Implementations（运行时实现）**：Agent 运行时（SimpleRuntime, DeepRuntime）

**依赖规则**：
- 依赖 Domain 和 Application Layer（实现它们的接口）
- 不依赖 Interfaces Layer

### 4. Interfaces Layer（接口层）

**职责**：处理外部世界交互，适配不同输入/输出方式。

**包含**：
- **HTTP Routes**：REST API 路由
- **WebSocket Handlers**：WebSocket 连接处理
- **CLI Commands**：命令行接口

**依赖规则**：
- 依赖 Application Layer（调用用例）
- 不直接依赖 Domain 或 Infrastructure Layer

## 依赖方向

```
Interfaces → Application → Domain ← Infrastructure
```

**核心原则**：
- 依赖向内指向 Domain Layer
- 外层通过接口使用内层
- 内层不感知外层存在

## 命名规范

### 目录命名
- 全部使用**复数**形式：`models/`, `services/`, `repositories/`
- 小写 + 下划线：`dialog_models/`, `tool_manager/`

### 文件命名
- 模块名使用小写 + 下划线：`dialog_manager.py`
- 协议文件统一使用 `protocols.py` 或 `interfaces.py`

### 类命名
- **实体**：名词，单数形式，首字母大写（`Dialog`, `Session`, `Skill`）
- **服务**：`*Service` 后缀（`DialogService`, `SkillService`）
- **仓库**：`*Repository` 后缀（`DialogRepository`）
- **DTO**：`*DTO` 或 `*Data` 后缀（`MessageDTO`, `SendMessageData`）

### 导入规范

```python
# 推荐：从具体模块导入
from backend.domain.models.dialog import Dialog, DialogSession
from backend.domain.models.shared.types import MessageDict

# 不推荐：使用通配符导入
from backend.domain.models import *

# 推荐：类型别名导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.infrastructure.services import ToolManager
```

## 常见导入路径

```python
# 配置
from backend.domain.models.shared.config import EngineConfig

# 领域模型
from backend.domain.models.dialog import Dialog, DialogSession, DialogSessionManager
from backend.domain.models.agent import Skill, ToolCall
from backend.domain.models.events import MessageReceived, ToolCallStarted

# DTO
from backend.application.dto import SendMessageRequest, SendMessageResponse

# 服务
from backend.application.services import DialogService, SkillService

# 基础设施
from backend.infrastructure.runtime import SimpleRuntime, EventBus
from backend.infrastructure.providers import LiteLLMProvider
```

## 目录深度限制

为了保持代码可导航性，目录深度限制为 **5 层**：

```
backend/domain/models/dialog/session.py  # 4 层 ✓
backend/infrastructure/runtime/deep.py   # 3 层 ✓
```

## 迁移指南

### 从旧架构迁移

1. **更新导入路径**：
   - `from core.xxx` → `from backend.xxx`
   - `from interfaces.xxx` → `from backend.interfaces.xxx`
   - `from runtime.xxx` → `from backend.runtime.xxx`

2. **模型位置变更**：
   - `core/models/entities/dialog.py` → `backend/domain/models/dialog/dialog.py`
   - `core/types/types.py` → `backend/domain/models/shared/types.py`

3. **运行时位置变更**：
   - `core/agent/runtimes/simple_runtime.py` → `backend/infrastructure/runtime/simple.py`

## 测试策略

- **Domain Layer**：单元测试，不依赖外部资源
- **Application Layer**：用例测试，Mock 外部依赖
- **Infrastructure Layer**：集成测试，测试真实外部服务
- **Interfaces Layer**：API 测试，端到端测试

## 相关文档

- `CLAUDE.md` - 项目整体架构指南
- `docs/ARCHITECTURE_COMPLETE.md` - 完整架构文档
- `docs/MIGRATION_GUIDE.md` - 迁移指南

---

*最后更新：2026-04-04*
