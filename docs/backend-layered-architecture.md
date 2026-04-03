# 后端分层架构设计

## 1. 新目录结构设计

```
core/
├── domain/                    # Domain 层 - 核心业务实体与规则
│   ├── __init__.py
│   ├── entities/              # 领域实体
│   │   ├── dialog.py          # Dialog, Message, ToolCall
│   │   ├── skill.py           # Skill 实体
│   │   └── events.py          # 领域事件 (DialogCreated, MessageReceived...)
│   ├── value_objects/         # 值对象
│   │   ├── message_content.py
│   │   └── tool_result.py
│   └── repositories/          # 仓库接口 (抽象)
│       ├── dialog_repository.py
│       └── memory_repository.py
│
├── application/               # Application/Service 层 - 用例编排
│   ├── __init__.py
│   ├── services/              # 应用服务
│   │   ├── dialog_service.py  # 对话用例 (create, send_message, close)
│   │   ├── skill_service.py   # 技能用例
│   │   └── memory_service.py  # 记忆用例
│   ├── dto/                   # 数据传输对象 (已存在 core/models/dto.py)
│   │   ├── requests.py        # 输入 DTO
│   │   └── responses.py       # 输出 DTO
│   └── interfaces/            # 应用层接口
│       └── agent_runtime.py   # IAgentRuntime 迁移至此
│
├── infrastructure/            # Infrastructure 层 - 技术实现
│   ├── __init__.py
│   ├── persistence/           # 数据持久化
│   │   ├── memory/            # 内存存储实现
│   │   │   └── dialog_repo.py
│   │   └── file/              # 文件存储实现
│   │       └── memory_repo.py
│   ├── messaging/             # 消息/事件
│   │   └── event_bus.py       # 从 runtime/ 迁移
│   ├── llm/                   # LLM Provider
│   │   ├── base.py
│   │   └── litellm_provider.py
│   └── config/                # 配置管理
│       └── engine_config.py
│
├── capabilities/              # Capabilities 层 - 领域能力 (保留现有接口)
│   ├── __init__.py
│   └── interfaces.py          # IDialogManager, IToolManager, etc.
│
├── runtime/                   # Runtime 层 - Agent 运行时
│   ├── __init__.py
│   ├── interfaces.py          # IAgentRuntime, IAgentRuntimeFactory
│   ├── factory.py
│   └── impl/                  # 运行时实现
│       ├── simple_runtime.py
│       └── deep_runtime.py
│
└── bridge/                    # Bridge 层 - 运行时与传输层桥接
    ├── __init__.py
    ├── interfaces.py          # IAgentRuntimeBridge
    └── agent_bridge.py

interfaces/                    # Interface 层 - 外部接口 (API/WebSocket)
├── __init__.py
├── http/                      # HTTP REST API
│   ├── __init__.py
│   ├── server.py
│   ├── dependencies.py        # FastAPI dependencies
│   └── routes/
│       ├── __init__.py
│       ├── dialog.py          # 对话路由
│       ├── skills.py          # 技能路由
│       ├── tools.py           # 工具路由
│       └── health.py          # 健康检查
├── websocket/                 # WebSocket 接口
│   ├── __init__.py
│   ├── server.py
│   └── manager.py             # WebSocket 连接管理
└── agent_runtime_bridge.py    # 桥接层入口

runtime/                       # 待迁移/合并到 infrastructure/messaging/
├── event_bus.py               # 迁移到 core/infrastructure/messaging/
└── logging_config.py

# 废弃/合并:
# - core/managers/ -> 合并到 core/application/services/ 和 core/capabilities/
# - core/models/ -> 拆分到 core/domain/entities/ 和 core/application/dto/
# - core/providers/ -> 合并到 core/infrastructure/llm/
# - core/tools/ -> 合并到 core/capabilities/ 或独立 skill 包
# - core/hitl/ -> 合并到 core/application/services/
# - core/plugins/ -> 合并到 core/application/ 或独立扩展点
```

## 2. 各层职责说明

### 2.1 Domain 层 (核心层)

**职责**: 包含业务核心实体、值对象、领域事件、业务规则

**关键内容**:
- `Dialog`, `Message`, `ToolCall` 实体
- `DialogCreated`, `MessageReceived` 等领域事件
- 仓库接口抽象 (`IDialogRepository`)

**依赖**: 无依赖，最纯净层

**设计原则**:
- 不包含任何技术实现细节
- 实体使用 Pydantic BaseModel 定义
- 业务规则在实体方法中实现

### 2.2 Application/Service 层

**职责**: 编排领域对象完成业务用例，协调各领域服务

**关键内容**:
- `DialogService`: 处理对话生命周期用例
- `SkillService`: 处理技能加载、管理用例
- `MemoryService`: 处理记忆总结、存储用例
- DTO 定义 (Request/Response)

**依赖**: 仅依赖 Domain 层

**设计原则**:
- 不包含业务规则，只编排流程
- 通过仓库接口操作数据，不直接访问数据库
- 返回 DTO 而非原始实体

### 2.3 Capabilities 层

**职责**: 定义领域能力接口，作为运行时与领域层的契约

**关键内容**:
- `IDialogManager`: 对话管理能力接口
- `IToolManager`: 工具管理能力接口
- `ISkillManager`: 技能管理能力接口
- `IMemoryManager`: 记忆管理能力接口

**依赖**: 依赖 Domain 层实体

**设计原则**:
- 接口定义稳定，实现可替换
- 作为依赖注入的抽象边界

### 2.4 Infrastructure 层

**职责**: 提供技术实现，支撑上层运行

**关键内容**:
- **Persistence**: 内存/文件/数据库存储实现
- **Messaging**: 事件总线实现
- **LLM**: LLM Provider 实现
- **Config**: 配置管理

**依赖**: 依赖 Domain 层 (实现仓库接口)

**设计原则**:
- 实现 Domain 层定义的仓库接口
- 包含所有外部依赖 (数据库、HTTP 客户端等)
- 可替换的实现 (内存 vs 文件 vs 数据库)

### 2.5 Runtime 层

**职责**: Agent 运行时实现，执行对话循环

**关键内容**:
- `IAgentRuntime`: 运行时统一接口
- `SimpleRuntime`: 简单对话运行时
- `DeepRuntime`: Deep Agent 运行时
- `AgentRuntimeFactory`: 运行时工厂

**依赖**: 依赖 Capabilities 层接口

**设计原则**:
- 通过 Capabilities 接口使用领域能力
- 不直接操作实体或仓库
- 运行时类型可切换 (simple/deep)

### 2.6 Bridge 层

**职责**: 桥接 Runtime 与传输层，协调事件广播

**关键内容**:
- `IAgentRuntimeBridge`: 桥接接口
- `AgentRuntimeBridge`: 实现类
- `IWebSocketBroadcaster`: WebSocket 广播接口

**依赖**: 依赖 Runtime 层和 Interface 层

**设计原则**:
- 解耦运行时与传输细节
- 统一事件转换和广播

### 2.7 Interface 层

**职责**: 对外暴露接口，处理协议细节

**关键内容**:
- **HTTP**: REST API 路由
- **WebSocket**: 实时通信
- 请求/响应序列化
- 认证/授权 (未来)

**依赖**: 依赖 Bridge 层

**设计原则**:
- 无业务逻辑，仅参数解析和调用转发
- 通过 Bridge 层与核心交互
- 处理协议特定细节 (HTTP 状态码、WebSocket 事件格式)

## 3. 依赖关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Interface 层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ HTTP Routes │  │ WebSocket   │  │ AgentRuntimeBridge      │  │
│  │             │  │ Manager     │  │ (桥接层入口)             │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          │                │    ┌────────────────┘
          │                │    │
          │                │    ▼
          │                │ ┌──────────────────────────────────┐
          │                │ │        Bridge 层                  │
          │                │ │  ┌────────────────────────────┐  │
          │                │ │  │ IAgentRuntimeBridge        │  │
          │                │ │  │ - 协调 Runtime 与 WebSocket │  │
          │                │ │  └────────────┬───────────────┘  │
          │                │ └───────────────┼──────────────────┘
          │                │                 │
          │                │                 ▼
          │                │ ┌──────────────────────────────────┐
          │                │ │        Runtime 层                 │
          │                │ │  ┌────────────────────────────┐  │
          │                │ │  │ IAgentRuntime              │  │
          │                │ │  │ - SimpleRuntime            │  │
          │                │ │  │ - DeepRuntime              │  │
          │                │ │  └────────────┬───────────────┘  │
          │                │ └───────────────┼──────────────────┘
          │                │                 │
          │                │                 ▼
          │                │ ┌──────────────────────────────────┐
          │                │ │      Capabilities 层              │
          │                │ │  ┌─────────┐ ┌─────────┐         │  │
          │                │ │  │IDialog  │ │ ITool   │         │  │
          │                │ │  │Manager  │ │Manager  │  ...    │  │
          │                │ │  └────┬────┘ └────┬────┘         │  │
          │                │ └───────┼─────────┼────────────────┘
          │                │         │         │
          │                │         ▼         ▼
          │                │ ┌──────────────────────────────────┐
          │                │ │      Application 层               │
          │                │ │  ┌─────────┐ ┌─────────┐         │  │
          │                │ │  │ Dialog  │ │ Skill   │         │  │
          │                │ │  │Service  │ │Service  │  ...    │  │
          │                │ │  └────┬────┘ └────┬────┘         │  │
          │                │ └───────┼─────────┼────────────────┘
          │                │         │         │
          │                │         ▼         ▼
          │                │ ┌──────────────────────────────────┐
          │                │ │         Domain 层                 │
│         │                │ │  ┌─────────┐ ┌─────────┐         │  │
│         │                │ │  │ Dialog  │ │ Message │         │  │
│         │                │ │  │ Entity  │ │ Entity  │  ...    │  │
│         │                │ │  └─────────┘ └─────────┘         │  │
│         │                │ └──────────────────────────────────┘
│         │                │
│         │                ▼
│         │   ┌──────────────────────────────────┐
│         │   │     Infrastructure 层             │
│         │   │  ┌─────────┐ ┌─────────┐         │
│         │   │  │Memory   │ │ File    │         │
│         │   │  │Storage  │ │ Storage │  ...    │
│         │   │  └─────────┘ └─────────┘         │
│         │   └──────────────────────────────────┘
│         │
│         └──────────────────────────────► (通过 Bridge 层间接依赖)
│
└─────────────────────────────────────────────────────────────────┘

依赖规则 (Dependency Rule):
───────────────────────────────────────────────────────────────────
上层 ──────────────────────────────────────────────► 下层
Interface ──► Bridge ──► Runtime ──► Capabilities ──► Application ──► Domain
                                              │
                                              ▼
                                       Infrastructure

关键原则:
1. 依赖只能向内指向更稳定的层
2. Domain 层不依赖任何其他层
3. Infrastructure 实现 Domain 定义的接口
4. 层间通过接口交互，不依赖具体实现
```

## 4. 关键接口定义

### 4.1 Domain 层 - 仓库接口

```python
# core/domain/repositories/dialog_repository.py
from abc import ABC, abstractmethod
from typing import Optional, List
from core.domain.entities.dialog import Dialog

class IDialogRepository(ABC):
    """对话仓库接口"""

    @abstractmethod
    async def save(self, dialog: Dialog) -> None:
        """保存对话"""
        pass

    @abstractmethod
    async def get(self, dialog_id: str) -> Optional[Dialog]:
        """获取对话"""
        pass

    @abstractmethod
    async def list_all(self) -> List[Dialog]:
        """列出所有对话"""
        pass

    @abstractmethod
    async def delete(self, dialog_id: str) -> None:
        """删除对话"""
        pass
```

### 4.2 Application 层 - 服务接口

```python
# core/application/services/dialog_service.py
from typing import AsyncIterator, Optional
from core.application.dto.requests import SendMessageRequest
from core.application.dto.responses import DialogResponse, MessageResponse

class DialogService:
    """对话应用服务"""

    def __init__(
        self,
        dialog_repo: IDialogRepository,
        event_bus: IEventBus,
        runtime: IAgentRuntime
    ):
        self._repo = dialog_repo
        self._event_bus = event_bus
        self._runtime = runtime

    async def create_dialog(self, user_input: str, title: Optional[str] = None) -> str:
        """创建对话用例"""
        dialog = Dialog.create(title)
        dialog.add_message(Message.user(user_input))
        await self._repo.save(dialog)
        self._event_bus.emit(DialogCreated(dialog_id=dialog.id))
        return dialog.id

    async def send_message(
        self,
        dialog_id: str,
        content: str
    ) -> AsyncIterator[str]:
        """发送消息用例"""
        async for chunk in self._runtime.send_message(dialog_id, content):
            yield chunk
```

### 4.3 Capabilities 层 - 能力接口 (已存在)

```python
# core/capabilities/interfaces.py (已存在)
class IDialogManager(ABC):
    @abstractmethod
    async def create(self, user_input: str, title: Optional[str] = None) -> str: ...

class IToolManager(ABC):
    @abstractmethod
    async def execute(self, dialog_id: str, tool_call: BaseModel) -> str: ...
```

### 4.4 Runtime 层 - 运行时接口 (已存在)

```python
# core/runtime/interfaces.py (已存在)
class IAgentRuntime(ABC):
    @abstractmethod
    async def send_message(self, dialog_id: str, message: str) -> AsyncIterator[AgentEvent]: ...

class IAgentRuntimeFactory(ABC):
    @abstractmethod
    def create(self, agent_type: str, agent_id: str, config: BaseModel) -> IAgentRuntime: ...
```

### 4.5 Bridge 层 - 桥接接口 (已存在)

```python
# core/bridge/interfaces.py (已存在)
class IAgentRuntimeBridge(ABC):
    @abstractmethod
    async def run_agent(self, dialog_id: str, content: str) -> None: ...

    @abstractmethod
    async def create_dialog(self, user_input: str, title: Optional[str] = None) -> str: ...
```

### 4.6 Interface 层 - FastAPI 路由

```python
# interfaces/http/routes/dialog.py
from fastapi import APIRouter, Depends
from core.bridge.interfaces import IAgentRuntimeBridge

router = APIRouter()

def get_bridge() -> IAgentRuntimeBridge:
    # 从容器解析
    return container.resolve(IAgentRuntimeBridge)

@router.post("/dialogs")
async def create_dialog(
    request: CreateDialogRequest,
    bridge: IAgentRuntimeBridge = Depends(get_bridge)
):
    """纯路由，无业务逻辑"""
    dialog_id = await bridge.create_dialog(request.user_input, request.title)
    return {"dialog_id": dialog_id}
```

## 5. 迁移路径

### 阶段 1: 建立新结构 (不破坏现有代码)
```bash
# 1. 创建新目录
mkdir -p core/domain/entities core/domain/repositories
mkdir -p core/application/services core/application/dto
mkdir -p core/infrastructure/persistence/memory
mkdir -p core/infrastructure/llm

# 2. 迁移 Domain 实体
# core/models/dialog.py -> core/domain/entities/dialog.py
# core/models/domain.py -> core/domain/entities/skill.py
# core/models/events.py -> core/domain/entities/events.py

# 3. 迁移 Infrastructure
# runtime/event_bus.py -> core/infrastructure/messaging/event_bus.py
# core/providers/ -> core/infrastructure/llm/
# core/infra/ -> core/infrastructure/persistence/
```

### 阶段 2: 重构 Application 层
```bash
# 1. 将 managers 重构为 services
# core/managers/dialog_manager.py -> core/application/services/dialog_service.py
# core/managers/skill_manager.py -> core/application/services/skill_service.py

# 2. 保持 Facade (AgentEngine) 作为兼容层
# core/engine.py 保留，内部委托给新的 Service 层
```

### 阶段 3: 重构 Interface 层
```bash
# 1. 路由瘦身
# interfaces/http/routes/*.py 移除业务逻辑，仅保留参数解析

# 2. 引入 Bridge 层
# 将 main.py 中的 WebSocket 广播逻辑移到 Bridge 层
```

### 阶段 4: 清理旧代码
```bash
# 1. 删除已迁移的旧文件
# 2. 更新所有导入语句
# 3. 运行测试验证
```

## 6. 当前架构 vs 目标架构对比

| 当前 | 目标 | 说明 |
|------|------|------|
| `core/managers/` | `core/application/services/` | 明确为应用服务层 |
| `core/models/` | `core/domain/entities/` + `core/application/dto/` | 分离领域实体和 DTO |
| `core/providers/` | `core/infrastructure/llm/` | 归入基础设施层 |
| `runtime/event_bus.py` | `core/infrastructure/messaging/` | 归入基础设施层 |
| `core/infra/` | `core/infrastructure/persistence/` | 统一基础设施命名 |
| `main.py` 直接依赖 Engine | `main.py` 依赖 Bridge 层 | 增加桥接层解耦 |
| Facade 模式 (AgentEngine) | 保留 + 新增 Service 层 | 保持兼容，内部重构 |

## 7. 关键设计决策

### 7.1 为什么保留 Capabilities 层？
- 作为 Runtime 和 Application 之间的契约层
- 允许运行时切换而不影响应用服务
- 已存在且设计良好，无需改动

### 7.2 为什么新增 Bridge 层？
- 解耦 Runtime 与传输层 (WebSocket)
- 统一事件转换逻辑
- 支持多种传输方式 (HTTP SSE, WebSocket, 未来 gRPC)

### 7.3 为什么 Domain 层使用 Pydantic？
- 与现有代码一致
- 天然支持序列化/验证
- 类型安全

### 7.4 如何处理现有 AgentEngine Facade？
- 保留作为兼容层
- 内部逐步委托给新的 Service 层
- 最终可标记为 deprecated
