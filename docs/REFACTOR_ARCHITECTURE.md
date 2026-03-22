# learn-claude-code-my 重构设计方案

基于 Hanako Core 设计思想的架构重构

---

## 1. 当前架构问题分析

### 1.1 现有结构

```
agents/
├── api/main_new.py          # 入口混杂了路由+业务逻辑
├── agent/s_full.py          # Agent 实现
├── base/                    # 基础组件
├── hooks/                   # Hook 实现（与业务耦合）
├── models/                  # Pydantic 模型
├── monitoring/              # 监控系统
├── plugins/                 # 插件系统
├── providers/               # LLM 提供商
├── session/                 # 会话管理
├── utils/                   # 工具函数
└── websocket/               # WebSocket 实现
```

### 1.2 主要问题

| 问题 | 说明 | 影响 |
|------|------|------|
| 层级不清 | api/ 既处理 HTTP 又包含业务逻辑 | 难以测试、职责混乱 |
| Hook 系统复杂 | Hooks 与状态管理深度耦合 | 扩展困难、调试困难 |
| 依赖关系混乱 | 循环导入、全局状态 | 维护成本高 |
| 缺乏统一门面 | 外部需要了解内部多个模块 | 使用困难 |

---

## 2. 重构目标架构

基于 Hanako 的 **Facade + 依赖注入 + 事件总线** 设计思想：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          重构后架构 (Hanako-style)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        Interface Layer (接口层)                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │  │
│  │  │  FastAPI    │  │  WebSocket  │  │    CLI      │  │   Testing    │ │  │
│  │  │   Router    │  │   Handler   │  │   Handler   │  │    Mock      │ │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘ │  │
│  │         └─────────────────┴─────────────────┴─────────────────┘        │  │
│  │                              │                                         │  │
│  │                    interfaces/  (仅做协议转换)                          │  │
│  └──────────────────────────────┼─────────────────────────────────────────┘  │
│                                 │                                            │
│  ┌──────────────────────────────┼─────────────────────────────────────────┐  │
│  │                         Core Layer (核心层)                            │  │
│  │                              │                                         │  │
│  │   ┌──────────────────────────┴─────────────────────────────────────┐   │  │
│  │   │                     AgentEngine (Facade)                       │   │  │
│  │   │                      core/engine.py                            │   │  │
│  │   │                                                                │   │  │
│  │   │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐  │   │  │
│  │   │  │  Dialog    │ │   Tool     │ │   Skill    │ │   State    │  │   │  │
│  │   │  │  Manager   │ │  Manager   │ │  Manager   │ │  Manager   │  │   │  │
│  │   │  └────────────┘ └────────────┘ └────────────┘ └────────────┘  │   │  │
│  │   │  ┌────────────┐ ┌────────────┐ ┌────────────┐                │   │  │
│  │   │  │  Memory    │ │  Provider  │ │  Session   │                │   │  │
│  │   │  │  Manager   │ │  Manager   │ │  Manager   │                │   │  │
│  │   │  └────────────┘ └────────────┘ └────────────┘                │   │  │
│  │   └────────────────────────────────────────────────────────────────┘   │  │
│  │                                    │                                    │  │
│  │   ┌────────────────────────────────┴────────────────────────────────┐  │  │
│  │   │                      Dialog Instance                             │  │  │
│  │   │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │  │  │
│  │   │  │  Message   │ │   Todo     │ │  Context   │ │  Artifact  │   │  │  │
│  │   │  │   Store    │ │   Store    │ │  Manager   │ │   Store    │   │  │  │
│  │   │  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │  │  │
│  │   └──────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                         │  │
│  │   core/  (所有 Manager 通过依赖注入获取依赖，不直接引用 Engine)            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                          │
│  ┌─────────────────────────────────┼────────────────────────────────────────┐ │
│  │                     Runtime Layer (运行时层)                            │ │
│  │                                 │                                       │ │
│  │   ┌─────────────────────────────┴────────────────────────────────────┐  │ │
│  │   │                        EventBus (事件总线)                        │  │ │
│  │   │                     runtime/event_bus.py                          │  │ │
│  │   │                                                                  │  │ │
│  │   │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │  │ │
│  │   │  │  Event     │ │  Stream    │ │  Plugin    │ │  Lifecycle │    │  │ │
│  │   │  │  Router    │ │  Handler   │ │  Registry  │ │  Manager   │    │  │ │
│  │   │  └────────────┘ └────────────┘ └────────────┘ └────────────┘    │  │ │
│  │   └──────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                         │ │
│  │   runtime/  (解耦 Core 和 Interface，异步事件驱动)                        │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 详细目录结构设计

### 3.1 核心层 (core/)

```
core/
├── __init__.py
├── engine.py                     # AgentEngine - Facade 门面
├── managers/                     # 所有 Manager 集中管理
│   ├── __init__.py
│   ├── dialog_manager.py         # 对话管理 (原 DialogStore 重构)
│   ├── tool_manager.py           # 工具管理 (原 tools 重构)
│   ├── skill_manager.py          # 技能管理 (原 skills 重构)
│   ├── state_manager.py          # 状态管理 (原 hooks/state 重构)
│   ├── memory_manager.py         # 记忆管理 (原 memory 重构)
│   ├── provider_manager.py       # LLM 提供商管理 (原 providers 重构)
│   └── session_manager.py        # 会话生命周期管理
├── models/                       # 领域模型 (从 models/ 迁移)
│   ├── __init__.py
│   ├── dialog.py                 # Dialog, Message, ToolCall
│   ├── events.py                 # 核心事件定义
│   ├── skill.py                  # Skill 定义
│   └── artifact.py               # Artifact 定义
├── stores/                       # 数据存储抽象
│   ├── __init__.py
│   ├── message_store.py          # 消息存储 (内存/持久化)
│   ├── todo_store.py             # Todo 存储
│   ├── artifact_store.py         # Artifact 存储
│   └── memory_store.py           # 记忆存储
└── exceptions.py                 # 核心异常定义
```

### 3.2 接口层 (interfaces/)

```
interfaces/
├── __init__.py
├── http/                         # HTTP REST API
│   ├── __init__.py
│   ├── server.py                 # FastAPI 应用创建
│   ├── routes/                   # 路由定义 (无业务逻辑)
│   │   ├── __init__.py
│   │   ├── dialog.py             # /api/dialog/*
│   │   ├── skills.py             # /api/skills/*
│   │   ├── tools.py              # /api/tools/*
│   │   └── health.py             # /api/health
│   └── middleware/               # HTTP 中间件
│       ├── cors.py
│       ├── auth.py
│       └── logging.py
├── websocket/                    # WebSocket 接口
│   ├── __init__.py
│   ├── server.py                 # WebSocket 服务器
│   ├── handlers/                 # 消息处理器
│   │   ├── __init__.py
│   │   ├── dialog_handler.py
│   │   └── system_handler.py
│   └── connection_manager.py     # 连接管理 (单例)
├── cli/                          # 命令行接口 (未来扩展)
│   └── __init__.py
└── adapters/                     # 外部系统适配器
    ├── __init__.py
    ├── litellm_adapter.py        # LiteLLM 适配
    └── file_system_adapter.py    # 文件系统适配
```

### 3.3 运行时层 (runtime/)

```
runtime/
├── __init__.py
├── event_bus.py                  # 事件总线 (核心解耦机制)
├── events/                       # 事件定义
│   ├── __init__.py
│   ├── dialog_events.py          # 对话相关事件
│   ├── tool_events.py            # 工具相关事件
│   ├── system_events.py          # 系统事件
│   └── lifecycle_events.py       # 生命周期事件
├── stream/                       # 流处理
│   ├── __init__.py
│   ├── stream_handler.py         # 统一流处理
│   └── parsers/                  # 流解析器 (Hanako-style)
│       ├── __init__.py
│       ├── think_parser.py       # <think> 标签解析
│       └── xml_parser.py         # XML 标签解析
├── plugins/                      # 插件系统重构
│   ├── __init__.py
│   ├── registry.py               # 插件注册表
│   ├── loader.py                 # 插件加载器
│   └── hook_interface.py         # Hook 接口定义
└── lifecycle/                    # 生命周期管理
    ├── __init__.py
    ├── startup.py                # 启动流程
    └── shutdown.py               # 关闭流程
```

### 3.4 工具层 (tools/)

```
tools/
├── __init__.py
├── definitions/                  # 工具定义
│   ├── __init__.py
│   ├── file_tools.py             # 文件操作工具
│   ├── shell_tools.py            # 命令执行工具
│   └── search_tools.py           # 搜索工具
├── executors/                    # 工具执行器
│   ├── __init__.py
│   ├── local_executor.py         # 本地执行
│   └── sandbox_executor.py       # 沙箱执行 (未来)
└── registry.py                   # 工具注册表
```

### 3.5 技能层 (skills/)

```
skills/
├── __init__.py
├── loader.py                     # 技能加载器
├── builtin/                      # 内置技能
│   ├── __init__.py
│   ├── finance/                  # 财务技能
│   ├── agent-builder/            # Agent 构建技能
│   └── code-review/              # 代码审查技能
└── registry.py                   # 技能注册表
```

### 3.6 基础设施层 (infrastructure/)

```
infrastructure/
├── __init__.py
├── config.py                     # 配置管理 (集中式)
├── logging.py                    # 日志配置
├── persistence/                  # 持久化
│   ├── __init__.py
│   ├── database.py               # 数据库连接
│   ├── file_storage.py           # 文件存储
│   └── cache.py                  # 缓存
└── monitoring/                   # 监控
    ├── __init__.py
    ├── metrics.py                # 指标收集
    └── tracing.py                # 链路追踪
```

### 3.7 前端层 (web/ - 保持不变)

```
web/
├── src/
│   ├── app/                      # Next.js App Router
│   ├── components/               # React 组件
│   ├── hooks/                    # React Hooks
│   ├── stores/                   # 状态管理 (Zustand)
│   ├── types/                    # TypeScript 类型
│   └── lib/                      # 工具函数
```

---

## 4. 核心代码示例

### 4.1 Facade - AgentEngine

```python
# core/engine.py
"""
AgentEngine - 核心门面
所有外部交互都通过此类，内部委托给各 Manager
"""
from typing import Optional, AsyncIterator
from core.managers.dialog_manager import DialogManager
from core.managers.tool_manager import ToolManager
from core.managers.skill_manager import SkillManager
from core.managers.state_manager import StateManager
from core.managers.memory_manager import MemoryManager
from core.managers.provider_manager import ProviderManager
from runtime.event_bus import EventBus

class AgentEngine:
    """Agent 核心引擎 - Facade 模式"""
    
    def __init__(self, config: dict):
        # 初始化基础设施
        self._config = config
        self._event_bus = EventBus()
        
        # 初始化 Manager (依赖注入)
        self._state_mgr = StateManager(
            event_bus=self._event_bus,
            config=config.get('state', {})
        )
        
        self._dialog_mgr = DialogManager(
            event_bus=self._event_bus,
            state_manager=self._state_mgr,
            config=config.get('dialog', {})
        )
        
        self._tool_mgr = ToolManager(
            event_bus=self._event_bus,
            config=config.get('tools', {})
        )
        
        self._skill_mgr = SkillManager(
            event_bus=self._event_bus,
            tool_manager=self._tool_mgr,
            config=config.get('skills', {})
        )
        
        self._memory_mgr = MemoryManager(
            event_bus=self._event_bus,
            config=config.get('memory', {})
        )
        
        self._provider_mgr = ProviderManager(
            event_bus=self._event_bus,
            config=config.get('provider', {})
        )
    
    # ═══════════════════════════════════════════════════
    # 对话管理 API (代理给 DialogManager)
    # ═══════════════════════════════════════════════════
    
    async def create_dialog(self, user_input: str) -> str:
        """创建新对话"""
        return await self._dialog_mgr.create(user_input)
    
    async def send_message(self, dialog_id: str, message: str) -> AsyncIterator[str]:
        """发送消息，返回流式响应"""
        async for chunk in self._dialog_mgr.send_message(dialog_id, message):
            yield chunk
    
    def get_dialog(self, dialog_id: str) -> Optional[Dialog]:
        """获取对话状态"""
        return self._dialog_mgr.get(dialog_id)
    
    # ═══════════════════════════════════════════════════
    # 工具管理 API (代理给 ToolManager)
    # ═══════════════════════════════════════════════════
    
    async def execute_tool(self, name: str, arguments: dict) -> dict:
        """执行工具"""
        return await self._tool_mgr.execute(name, arguments)
    
    def list_tools(self) -> list[ToolDefinition]:
        """列出可用工具"""
        return self._tool_mgr.list_available()
    
    # ═══════════════════════════════════════════════════
    # 技能管理 API (代理给 SkillManager)
    # ═══════════════════════════════════════════════════
    
    async def load_skill(self, skill_path: str) -> Skill:
        """加载技能"""
        return await self._skill_mgr.load(skill_path)
    
    # ═══════════════════════════════════════════════════
    # 事件订阅 API (代理给 EventBus)
    # ═══════════════════════════════════════════════════
    
    def subscribe(self, callback: Callable, event_types: list[str] = None):
        """订阅事件"""
        return self._event_bus.subscribe(callback, event_types)
    
    # ═══════════════════════════════════════════════════
    # 生命周期管理
    # ═══════════════════════════════════════════════════
    
    async def startup(self):
        """启动引擎"""
        await self._state_mgr.load()
        await self._skill_mgr.load_builtin_skills()
        self._event_bus.emit(SystemStarted())
    
    async def shutdown(self):
        """关闭引擎"""
        await self._state_mgr.save()
        self._event_bus.emit(SystemStopped())
```

### 4.2 Manager 实现 - 依赖注入示例

```python
# core/managers/dialog_manager.py
"""
DialogManager - 对话管理
通过构造函数注入依赖，不直接引用 Engine
"""
from typing import Callable
from runtime.event_bus import EventBus
from core.stores.message_store import MessageStore
from core.models.dialog import Dialog, Message
from runtime.events.dialog_events import (
    DialogCreated, MessageReceived, StreamDelta
)

class DialogManager:
    """对话管理器 - 依赖注入模式"""
    
    def __init__(
        self,
        event_bus: EventBus,                    # 依赖 1: 事件总线
        state_manager: 'StateManager',          # 依赖 2: 状态管理器
        memory_manager: Optional['MemoryManager'] = None,  # 可选依赖
        config: dict = None
    ):
        self._event_bus = event_bus
        self._state_mgr = state_manager
        self._memory_mgr = memory_manager
        self._config = config or {}
        
        # 数据存储
        self._store = MessageStore()
        self._active_dialogs: dict[str, Dialog] = {}
    
    async def create(self, user_input: str) -> str:
        """创建对话"""
        dialog = Dialog.from_user_input(user_input)
        self._active_dialogs[dialog.id] = dialog
        
        # 发射事件 (解耦的通知机制)
        self._event_bus.emit(DialogCreated(
            dialog_id=dialog.id,
            user_input=user_input
        ))
        
        return dialog.id
    
    async def send_message(
        self, 
        dialog_id: str, 
        message: str
    ) -> AsyncIterator[str]:
        """发送消息并流式返回"""
        dialog = self._get_dialog(dialog_id)
        
        # 添加用户消息
        user_msg = Message.user(message)
        dialog.add_message(user_msg)
        
        # 发射接收事件
        self._event_bus.emit(MessageReceived(
            dialog_id=dialog_id,
            message=user_msg
        ))
        
        # 调用 LLM (通过 provider，不直接耦合)
        provider = self._state_mgr.get_current_provider()
        
        # 流式处理
        full_response = []
        async for chunk in provider.chat(dialog.messages):
            full_response.append(chunk)
            
            # 发射流事件
            self._event_bus.emit(StreamDelta(
                dialog_id=dialog_id,
                delta=chunk
            ))
            
            yield chunk
        
        # 保存助手回复
        assistant_msg = Message.assistant(''.join(full_response))
        dialog.add_message(assistant_msg)
        
        # 触发记忆更新 (通过事件，不直接调用 MemoryManager)
        if self._memory_mgr:
            self._event_bus.emit(MessageCompleted(
                dialog_id=dialog_id,
                messages=dialog.messages
            ))
```

### 4.3 EventBus 实现

```python
# runtime/event_bus.py
"""
EventBus - 统一事件总线
解耦模块间通信，支持过滤订阅
"""
from typing import Callable, Optional
from dataclasses import dataclass
import asyncio

@dataclass
class EventFilter:
    """事件过滤器"""
    event_types: Optional[list[str]] = None
    dialog_id: Optional[str] = None

class EventBus:
    """事件总线 - 发布订阅模式"""
    
    def __init__(self):
        self._subscribers: dict[str, list[tuple[int, Callable, EventFilter]]] = {}
        self._next_id = 0
        self._lock = asyncio.Lock()
    
    def subscribe(
        self, 
        callback: Callable,
        event_types: list[str] = None,
        dialog_id: str = None
    ) -> Callable:
        """
        订阅事件
        
        Args:
            callback: 回调函数 (event) -> None
            event_types: 只接收这些类型的事件
            dialog_id: 只接收该对话的事件
            
        Returns:
            取消订阅函数
        """
        self._next_id += 1
        sub_id = self._next_id
        
        filter_key = event_types[0] if event_types else '__all__'
        
        if filter_key not in self._subscribers:
            self._subscribers[filter_key] = []
        
        self._subscribers[filter_key].append((
            sub_id,
            callback,
            EventFilter(event_types, dialog_id)
        ))
        
        # 返回取消订阅函数
        def unsubscribe():
            subs = self._subscribers.get(filter_key, [])
            self._subscribers[filter_key] = [
                s for s in subs if s[0] != sub_id
            ]
        
        return unsubscribe
    
    def emit(self, event: 'BaseEvent'):
        """
        发射事件
        
        事件会被异步分发给所有匹配的订阅者
        """
        event_type = event.__class__.__name__
        
        # 获取匹配的订阅者
        callbacks = []
        
        # 特定类型订阅者
        if event_type in self._subscribers:
            for sub_id, callback, filter in self._subscribers[event_type]:
                if self._matches_filter(event, filter):
                    callbacks.append(callback)
        
        # 通用订阅者
        if '__all__' in self._subscribers:
            for sub_id, callback, filter in self._subscribers['__all__']:
                if self._matches_filter(event, filter):
                    callbacks.append(callback)
        
        # 异步分发 (不阻塞发射者)
        asyncio.create_task(self._dispatch(event, callbacks))
    
    def _matches_filter(self, event: 'BaseEvent', filter: EventFilter) -> bool:
        """检查事件是否匹配过滤器"""
        # 检查对话 ID
        if filter.dialog_id and hasattr(event, 'dialog_id'):
            if event.dialog_id != filter.dialog_id:
                return False
        return True
    
    async def _dispatch(self, event: 'BaseEvent', callbacks: list[Callable]):
        """分发事件到所有订阅者"""
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                # 日志记录，不中断其他订阅者
                print(f"Event handler error: {e}")
```

### 4.4 HTTP 接口层 - 纯协议转换

```python
# interfaces/http/routes/dialog.py
"""
Dialog HTTP 路由
只做协议转换，无业务逻辑
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from core.engine import AgentEngine
from interfaces.http.dependencies import get_engine
from interfaces.http.schemas import (
    CreateDialogRequest,
    CreateDialogResponse,
    SendMessageRequest
)

router = APIRouter(prefix="/api/dialog", tags=["dialog"])

@router.post("/create", response_model=CreateDialogResponse)
async def create_dialog(
    request: CreateDialogRequest,
    engine: AgentEngine = Depends(get_engine)
):
    """创建新对话"""
    try:
        dialog_id = await engine.create_dialog(request.user_input)
        return CreateDialogResponse(dialog_id=dialog_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{dialog_id}/send")
async def send_message(
    dialog_id: str,
    request: SendMessageRequest,
    engine: AgentEngine = Depends(get_engine)
):
    """发送消息，SSE 流式返回"""
    async def event_generator():
        async for chunk in engine.send_message(dialog_id, request.message):
            yield {"data": chunk}
    
    return EventSourceResponse(event_generator())

@router.get("/{dialog_id}")
async def get_dialog(
    dialog_id: str,
    engine: AgentEngine = Depends(get_engine)
):
    """获取对话状态"""
    dialog = engine.get_dialog(dialog_id)
    if not dialog:
        raise HTTPException(status_code=404, detail="Dialog not found")
    return dialog
```

### 4.5 WebSocket 接口层

```python
# interfaces/websocket/handlers/dialog_handler.py
"""
WebSocket Dialog 处理器
订阅 Engine 事件并转发到 WebSocket
"""
import json
from core.engine import AgentEngine
from runtime.event_bus import EventBus
from runtime.events.dialog_events import (
    DialogCreated, MessageReceived, StreamDelta
)

class WebSocketDialogHandler:
    """WebSocket 对话处理器"""
    
    def __init__(
        self,
        engine: AgentEngine,
        connection_manager: 'ConnectionManager'
    ):
        self._engine = engine
        self._conn_mgr = connection_manager
        self._unsubscribe = None
    
    async def start(self):
        """启动处理器，订阅事件"""
        self._unsubscribe = self._engine.subscribe(
            self._on_event,
            event_types=[
                'DialogCreated',
                'MessageReceived', 
                'StreamDelta',
                'MessageCompleted',
                'ToolCallStarted',
                'ToolCallCompleted'
            ]
        )
    
    async def stop(self):
        """停止处理器，取消订阅"""
        if self._unsubscribe:
            self._unsubscribe()
    
    async def _on_event(self, event: 'BaseEvent'):
        """处理引擎事件，转发到 WebSocket"""
        # 序列化事件
        message = {
            'type': event.__class__.__name__,
            'data': self._serialize_event(event)
        }
        
        # 广播到所有连接 (或特定对话的订阅者)
        if hasattr(event, 'dialog_id'):
            await self._conn_mgr.broadcast_to_dialog(
                event.dialog_id,
                json.dumps(message)
            )
        else:
            await self._conn_mgr.broadcast(json.dumps(message))
    
    def _serialize_event(self, event: 'BaseEvent') -> dict:
        """序列化事件为字典"""
        # 使用 Pydantic 模型序列化
        if hasattr(event, 'model_dump'):
            return event.model_dump()
        return event.__dict__
```

---

## 5. 模块间依赖关系

```
依赖方向 (从上到下，上层依赖下层)

┌─────────────────────────────────────────────┐
│  interfaces/         ◄── 仅依赖 core.engine │
│  (http/websocket/cli)   和 runtime.events   │
├─────────────────────────────────────────────┤
│  core/               ◄── 依赖 runtime       │
│  (engine/managers)      和 infrastructure   │
├─────────────────────────────────────────────┤
│  runtime/            ◄── 仅依赖 core.models │
│  (event_bus/stream)     (事件数据定义)       │
├─────────────────────────────────────────────┤
│  tools/              ◄── 可独立运行          │
│  skills/                                    │
├─────────────────────────────────────────────┤
│  infrastructure/     ◄── 最底层，被所有层依赖 │
│  (config/logging/persistence)               │
└─────────────────────────────────────────────┘
```

---

## 6. 迁移路径

### 阶段 1: 创建新结构 (并行开发)

```bash
# 创建新目录结构
mkdir -p core/managers core/models core/stores
mkdir -p interfaces/http/routes interfaces/websocket/handlers
mkdir -p runtime/events runtime/stream runtime/plugins
```

### 阶段 2: 实现核心组件

1. 先实现 `runtime/event_bus.py` (事件总线)
2. 实现 `core/engine.py` (Facade)
3. 逐个迁移 Manager (dialog → tool → skill → state → memory)

### 阶段 3: 迁移接口层

1. 实现 `interfaces/http/server.py`
2. 迁移路由，将业务逻辑移到 Manager
3. 实现 WebSocket 处理器

### 阶段 4: 切换入口

```python
# 旧入口
# agents/api/main_new.py

# 新入口  
# main.py
from core.engine import AgentEngine
from interfaces.http.server import create_app
from infrastructure.config import load_config

async def main():
    config = load_config()
    engine = AgentEngine(config)
    await engine.startup()
    
    app = create_app(engine)
    await run_server(app)
```

---

## 7. 关键改进点总结

| 方面 | 重构前 | 重构后 (Hanako-style) | 收益 |
|------|--------|----------------------|------|
| **架构模式** | Hook 系统，深度耦合 | Facade + Manager | 职责清晰，易于测试 |
| **模块通信** | 直接调用，回调嵌套 | EventBus 发布订阅 | 彻底解耦，可扩展 |
| **依赖管理** | 循环导入，全局状态 | 构造函数注入 | 可测试，可替换 |
| **接口层** | 业务逻辑混杂在路由 | 纯协议转换 | 支持多协议 (HTTP/WS/CLI) |
| **数据流** | 双向混乱 | 单向: Engine → Event → Interface | 可预测，易调试 |

---

## 8. 文件清单

### 新增/重构文件列表 (约 40 个文件)

```
# 核心层 (15 files)
core/__init__.py
core/engine.py
core/managers/__init__.py
core/managers/dialog_manager.py
core/managers/tool_manager.py
core/managers/skill_manager.py
core/managers/state_manager.py
core/managers/memory_manager.py
core/managers/provider_manager.py
core/models/__init__.py
core/models/dialog.py
core/models/events.py
core/stores/__init__.py
core/stores/message_store.py
core/exceptions.py

# 运行时层 (8 files)
runtime/__init__.py
runtime/event_bus.py
runtime/events/__init__.py
runtime/events/dialog_events.py
runtime/events/tool_events.py
runtime/events/system_events.py
runtime/stream/__init__.py
runtime/stream/stream_handler.py

# 接口层 (10 files)
interfaces/__init__.py
interfaces/http/__init__.py
interfaces/http/server.py
interfaces/http/routes/__init__.py
interfaces/http/routes/dialog.py
interfaces/http/routes/skills.py
interfaces/http/routes/tools.py
interfaces/websocket/__init__.py
interfaces/websocket/server.py
interfaces/websocket/handlers/dialog_handler.py

# 基础设施 (5 files)
infrastructure/__init__.py
infrastructure/config.py
infrastructure/logging.py
infrastructure/persistence/__init__.py
infrastructure/persistence/database.py

# 入口 (2 files)
main.py
config.yaml
```

---

*设计基于 Hanako Core 架构思想*  
*文档版本: 1.0*  
*生成日期: 2026-03-19*
