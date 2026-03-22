# 代码迁移计划

## 当前状态分析

### 旧代码结构 (`.claude/worktrees/agent-a0b908b1/agents/`)

```
agents/
├── base/                       # 基础组件
│   ├── base_agent_loop.py     # BaseAgentLoop - 需要迁移到 SimpleAgent
│   ├── basetool.py            # WorkspaceOps - 已迁移到 core.tools
│   ├── toolkit.py             # @tool 装饰器 - 已迁移到 core.tools
│   ├── abstract/hooks.py      # AgentLifecycleHooks - 已在新架构中
│   └── plugin_enabled_agent.py # 插件启用 Agent
├── providers/                  # Provider 实现
│   ├── base.py                # BaseProvider
│   ├── litellm_provider.py    # LiteLLMProvider
│   ├── registry.py            # ProviderRegistry
│   └── tool_parser.py         # 工具解析
├── hooks/                      # 生命周期钩子 (需要迁移)
│   ├── agent_websocket_bridge.py
│   ├── session_history_hook.py
│   ├── context_compact_hook.py
│   ├── todo_manager_hook.py
│   └── sql_valid_hook.py
├── session/                    # 会话管理 (需要迁移)
│   ├── session_manager.py
│   ├── runtime_context.py
│   ├── history_utils.py
│   └── todo_hitl.py
├── plugins/                    # 插件系统 (需要迁移)
│   ├── compact_plugin.py
│   └── skill_plugin.py
├── api/                        # API 层 (需要迁移)
│   ├── main.py / main_new.py
│   ├── agent_bridge.py
│   └── session_hooks.py
├── core/                       # 核心消息类型
│   └── messages.py
└── models/                     # 数据模型
    ├── dialog_types.py
    └── openai_types.py
```

### 新架构状态 (`core/`)

```
core/                           # ✅ 已完成
├── types/                      # 基础类型
├── agent/                      # Agent 抽象和实现
├── tools/                      # 工具系统
└── providers/                  # Provider 层
```

---

## 迁移策略

采用**增量迁移**策略，保持旧代码可用，逐步替换：

```
Phase 1: 兼容性层 (Week 1)
Phase 2: API 层迁移 (Week 2)
Phase 3: 钩子系统迁移 (Week 3)
Phase 4: 插件系统迁移 (Week 4)
Phase 5: 清理旧代码 (Week 5)
```

---

## Phase 1: 兼容性层

目标: 让旧代码可以通过新架构使用

### 1.1 创建适配器模块

```python
# core/compat/__init__.py
"""
兼容性模块 - 桥接新旧架构

允许旧代码逐步迁移到新架构，而不需要一次性重写
"""

from .agent_adapter import BaseAgentLoopAdapter
from .hooks_adapter import LifecycleHooksAdapter

__all__ = ["BaseAgentLoopAdapter", "LifecycleHooksAdapter"]
```

### 1.2 Agent 适配器

```python
# core/compat/agent_adapter.py
"""
BaseAgentLoop 适配器

让新架构的 SimpleAgent 兼容旧代码的 BaseAgentLoop 接口
"""

from typing import List, Dict, Any
from ..agent.simple.agent import SimpleAgent
from ..tools import ToolRegistry


class BaseAgentLoopAdapter:
    """
    适配新架构 SimpleAgent 到旧 BaseAgentLoop 接口
    
    旧代码使用方式:
        agent = BaseAgentLoop(provider=..., model=..., tools=...)
        agent.run(messages)
    
    新代码使用方式:
        agent = BaseAgentLoopAdapter(provider=..., model=..., tools=...)
        agent.run(messages)  # 内部使用 SimpleAgent
    """
    
    def __init__(self, provider=None, model=None, system="", tools=None, 
                 tool_handlers=None, max_tokens=8000, max_rounds=25):
        from .. import AgentFactory
        
        self._agent = AgentFactory.create("simple", "adapted_agent")
        self._system = system
        
        # 转换工具格式
        tools_info = self._convert_tools(tools or [], tool_handlers or {})
        
        # 初始化
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            self._agent.initialize({
                "provider": provider,
                "model": model,
                "system": system,
                "tools": tools_info,
                "max_tokens": max_tokens,
                "max_rounds": max_rounds,
            })
        )
    
    def _convert_tools(self, tools, tool_handlers):
        """转换旧格式工具到新格式"""
        result = []
        for tool in tools:
            if isinstance(tool, dict):
                name = tool.get("function", {}).get("name", "unknown")
                handler = tool_handlers.get(name)
                result.append({
                    "name": name,
                    "handler": handler,
                    "description": tool.get("function", {}).get("description", ""),
                    "parameters": tool.get("function", {}).get("parameters", {}),
                })
        return result
    
    def run(self, messages: List[Dict[str, Any]]) -> str:
        """同步运行，兼容旧接口"""
        import asyncio
        
        # 获取最后一条用户消息
        user_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break
        
        if not user_msg:
            return "Error: No user message found"
        
        # 转换历史消息
        from ..types import AgentMessage
        context = [
            AgentMessage(role=m["role"], content=m["content"])
            for m in messages[:-1] if m.get("role") in ("user", "assistant", "system")
        ]
        
        # 运行
        result = asyncio.get_event_loop().run_until_complete(
            self._agent.run_sync(user_msg, context=context)
        )
        
        # 更新 messages 列表 (旧代码依赖这个副作用)
        messages.append({"role": "assistant", "content": result})
        
        return result
    
    def arun(self, messages: List[Dict[str, Any]]) -> str:
        """异步运行"""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self._async_run(messages))
    
    async def _async_run(self, messages):
        # 类似 run() 但 async
        pass
    
    def stop(self):
        """停止运行"""
        import asyncio
        asyncio.get_event_loop().run_until_complete(self._agent.stop())
    
    def set_hook_delegate(self, delegate):
        """设置钩子委托"""
        self._agent.set_hook_delegate(delegate)
```

### 1.3 钩子适配器

```python
# core/compat/hooks_adapter.py
"""
生命周期钩子适配器

桥接旧 HookName 枚举到新 HookName
"""

from ..types import HookName as NewHookName


class LifecycleHooksAdapter:
    """
    适配旧钩子系统到新架构
    
    旧代码:
        from agents.base.abstract import HookName
        class MyHooks:
            def on_hook(self, hook, **payload):
                if hook == HookName.ON_STREAM_TOKEN: ...
    
    新代码:
        from core.types import HookName
        class MyHooks(AgentLifecycleHooks):
            def on_hook(self, hook, **payload):
                if hook == HookName.ON_STREAM_TOKEN: ...
    """
    
    def __init__(self, legacy_hooks):
        self._legacy = legacy_hooks
    
    def on_hook(self, hook: NewHookName, **payload):
        """转换并转发到新钩子"""
        # HookName 枚举值相同，直接转发
        if self._legacy:
            try:
                self._legacy.on_hook(hook, **payload)
            except Exception:
                pass
```

---

## Phase 2: API 层迁移

### 2.1 新的 API 结构

```
api/
├── __init__.py
├── main.py              # FastAPI 应用入口
├── routes/
│   ├── __init__.py
│   ├── agent.py         # Agent 相关路由
│   ├── session.py       # Session 相关路由
│   └── websocket.py     # WebSocket 路由
├── dependencies.py      # 依赖注入
└── models.py            # Pydantic 模型
```

### 2.2 路由实现示例

```python
# api/routes/agent.py
from fastapi import APIRouter, Depends
from core import AgentFactory

router = APIRouter(prefix="/agent", tags=["agent"])

@router.post("/create")
async def create_agent(config: AgentConfig):
    """创建新的 Agent 实例"""
    agent = AgentFactory.create(config.type, config.agent_id)
    await agent.initialize(config.dict())
    return {"agent_id": agent.agent_id, "status": agent.status.value}

@router.post("/run/{agent_id}")
async def run_agent(agent_id: str, request: RunRequest):
    """运行 Agent"""
    # 获取或创建 Agent 实例
    agent = get_agent_instance(agent_id)
    
    # 流式返回
    async def event_stream():
        async for event in agent.run(request.message):
            yield f"data: {event.json()}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

---

## Phase 3: 钩子系统迁移

### 3.1 新钩子系统

```python
# core/hooks/__init__.py
"""
钩子系统 - 扩展 SimpleAgent 的功能

- ContextCompactHook: 上下文压缩
- SessionHistoryHook: 会话历史
- TodoManagerHook: Todo 管理
- SqlValidHook: SQL 验证
"""

from .base import HookManager
from .context_compact import ContextCompactHook
from .session_history import SessionHistoryHook
from .todo_manager import TodoManagerHook

__all__ = ["HookManager", "ContextCompactHook", "SessionHistoryHook", "TodoManagerHook"]
```

### 3.2 钩子管理器

```python
# core/hooks/base.py
from typing import List
from ..agent.interface import AgentLifecycleHooks
from ..types import HookName


class HookManager(AgentLifecycleHooks):
    """管理多个钩子的组合"""
    
    def __init__(self):
        self._hooks: List[AgentLifecycleHooks] = []
    
    def add(self, hook: AgentLifecycleHooks):
        self._hooks.append(hook)
    
    def remove(self, hook: AgentLifecycleHooks):
        self._hooks.remove(hook)
    
    def on_hook(self, hook: HookName, **payload):
        for h in self._hooks:
            try:
                h.on_hook(hook, **payload)
            except Exception as e:
                logger.error(f"Hook error: {e}")
```

---

## Phase 4: 插件系统迁移

### 4.1 新插件系统

```python
# core/plugins/__init__.py
"""
插件系统

- SkillPlugin: 技能加载
- CompactPlugin: 上下文压缩
"""

from .base import Plugin, PluginManager
from .skill_plugin import SkillPlugin
from .compact_plugin import CompactPlugin

__all__ = ["Plugin", "PluginManager", "SkillPlugin", "CompactPlugin"]
```

### 4.2 插件基类

```python
# core/plugins/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict


class Plugin(ABC):
    """插件基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    
    @abstractmethod
    async def on_before_run(self, context: Dict) -> None:
        pass
    
    @abstractmethod
    async def on_after_run(self, context: Dict) -> None:
        pass


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
    
    def register(self, plugin: Plugin):
        self._plugins[plugin.name] = plugin
    
    async def run_hook(self, hook_name: str, context: Dict):
        for plugin in self._plugins.values():
            method = getattr(plugin, hook_name, None)
            if method:
                await method(context)
```

---

## Phase 5: 会话管理迁移

### 5.1 新会话管理

```python
# core/session/__init__.py
"""
会话管理

- SessionManager: 管理多个会话
- Session: 单个会话的状态
- RuntimeContext: 运行时上下文
"""

from .manager import SessionManager
from .session import Session
from .runtime_context import RuntimeContext

__all__ = ["SessionManager", "Session", "RuntimeContext"]
```

---

## 迁移检查清单

### Phase 1: 兼容性层
- [ ] 创建 `core/compat/` 模块
- [ ] 实现 `BaseAgentLoopAdapter`
- [ ] 实现 `LifecycleHooksAdapter`
- [ ] 测试旧代码通过适配器使用新架构

### Phase 2: API 层
- [ ] 创建 `api/` 目录结构
- [ ] 迁移路由
- [ ] 迁移依赖注入
- [ ] 测试 API 端点

### Phase 3: 钩子系统
- [ ] 创建 `core/hooks/` 模块
- [ ] 迁移 ContextCompactHook
- [ ] 迁移 SessionHistoryHook
- [ ] 迁移 TodoManagerHook
- [ ] 迁移其他钩子

### Phase 4: 插件系统
- [ ] 创建 `core/plugins/` 模块
- [ ] 迁移 SkillPlugin
- [ ] 迁移 CompactPlugin

### Phase 5: 会话管理
- [ ] 创建 `core/session/` 模块
- [ ] 迁移 SessionManager
- [ ] 迁移 RuntimeContext

### Phase 6: 清理
- [ ] 更新所有导入
- [ ] 删除旧代码
- [ ] 更新文档

---

## 关键决策点

1. **是否保留 BaseAgentLoop 类名？**
   - 选项 A: 保留，作为 SimpleAgent 的别名
   - 选项 B: 重命名，使用新类名
   - 建议: 选项 A，减少迁移成本

2. **钩子系统如何兼容？**
   - 新架构使用 `HookName` 枚举
   - 旧代码可以直接使用新枚举
   - 提供适配器处理差异

3. **工具系统如何兼容？**
   - 新架构的 `WorkspaceOps` 已兼容旧接口
   - `@tool` 装饰器行为一致
   - 无需特殊适配

4. **Provider 如何兼容？**
   - 新架构的 `LiteLLMProvider` 已兼容旧接口
   - 可能需要处理 stream chunk 格式差异

---

## 立即开始

建议从 **Phase 1 兼容性层**开始，因为这是后续所有迁移的基础。你想现在开始实现吗？
