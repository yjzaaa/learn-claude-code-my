# 迁移指南 - 从旧代码到新架构

## 概述

本项目已按照**四层架构**进行重构：

```
core/
├── types/          # 共享类型定义
├── agent/          # Agent 抽象和实现
│   ├── interface.py     # AgentInterface 抽象基类
│   ├── factory.py       # AgentFactory 工厂模式
│   ├── simple/          # SimpleAgent 实现
│   └── adapters/        # SDK 适配器（预留）
├── tools/          # 工具系统
│   ├── toolkit.py       # @tool 装饰器
│   ├── registry.py      # ToolRegistry
│   └── workspace.py     # WorkspaceOps
└── providers/      # LLM Provider
    ├── base.py
    └── litellm_provider.py
```

---

## 快速迁移对照表

### 1. 创建 Agent

**旧代码 (BaseAgentLoop)**:
```python
from agents.base import BaseAgentLoop, WorkspaceOps
from agents.providers import create_provider_from_env

workspace = WorkspaceOps(Path.cwd())
agent = BaseAgentLoop(
    provider=create_provider_from_env(),
    model="deepseek-chat",
    system="You are helpful",
    tools=workspace.get_tools(),
)
```

**新代码 (AgentFactory)**:
```python
from core import AgentFactory
from core.tools import WorkspaceOps

workspace = WorkspaceOps(Path.cwd())
agent = AgentFactory.create("simple", agent_id="my_agent")

# 准备工具信息
tools_info = []
for tool_fn in workspace.get_tools():
    spec = getattr(tool_fn, "__tool_spec__", {})
    tools_info.append({
        "name": spec["name"],
        "handler": tool_fn,
        "description": spec["description"],
        "parameters": spec["parameters"],
    })

# 初始化
await agent.initialize({
    "model": "deepseek-chat",
    "system": "You are helpful",
    "tools": tools_info,
})
```

---

### 2. 运行 Agent

**旧代码**:
```python
messages = [{"role": "user", "content": "Hello"}]
result = agent.run(messages)  # 同步，非流式
```

**新代码**:
```python
# 流式（推荐）
async for event in agent.run("Hello"):
    if event.type == "text_delta":
        print(event.data, end="")
    elif event.type == "tool_start":
        print(f"\n[Tool: {event.data['name']}]")
    elif event.type == "complete":
        print("\n[Done]")

# 非流式（兼容旧代码）
result = await agent.run_sync("Hello")
```

---

### 3. 注册工具

**旧代码**:
```python
# 通过 WorkspaceOps 构建工具
workspace = WorkspaceOps(workdir)
TOOLS = workspace.get_tools()

# 或者手动构建
tools, tool_handlers = build_tools_and_handlers([my_function])
```

**新代码**:
```python
# 方式 1: 初始化时传入
tools_info = [{
    "name": "my_tool",
    "handler": my_function,
    "description": "...",
    "parameters": {...},
}]
await agent.initialize({"tools": tools_info})

# 方式 2: 动态注册
agent.register_tool(
    name="my_tool",
    handler=my_function,
    description="...",
    schema={...},
)
```

---

### 4. 生命周期钩子

**旧代码**:
```python
class MyHooks:
    def on_hook(self, hook, **payload):
        if hook == "ON_STREAM_TOKEN":
            print(payload["chunk"].content)

agent = BaseAgentLoop(...)
agent.set_hook_delegate(MyHooks())
```

**新代码**:
```python
from core.types import HookName
from core.agent.interface import AgentLifecycleHooks

class MyHooks(AgentLifecycleHooks):
    def on_hook(self, hook, **payload):
        if hook == HookName.ON_STREAM_TOKEN:
            print(payload["chunk"].content)

agent = AgentFactory.create("simple", "my_agent")
agent.set_hook_delegate(MyHooks())
```

---

## 事件类型对照

| 旧代码 | 新代码 (AgentEvent.type) | 说明 |
|--------|------------------------|------|
| `ON_BEFORE_RUN` | - | 内部使用 |
| `ON_STREAM_TOKEN` | `text_delta` / `reasoning_delta` | 流式输出 |
| `ON_TOOL_CALL` | `tool_start` | 工具开始 |
| `ON_TOOL_RESULT` | `tool_end` | 工具完成 |
| `ON_COMPLETE` | `complete` | 完成 |
| `ON_ERROR` | `error` | 错误 |
| `ON_STOP` | `stopped` | 用户停止 |
| `ON_AFTER_RUN` | - | 内部使用 |

---

## 类型对照

| 旧代码 | 新代码 |
|--------|--------|
| `BaseAgentLoop` | `SimpleAgent` |
| `BaseProvider` | `BaseProvider` (不变) |
| `LiteLLMProvider` | `LiteLLMProvider` (不变) |
| `WorkspaceOps` | `WorkspaceOps` (移动到 core.tools) |
| `tool` 装饰器 | `tool` 装饰器 (移动到 core.tools) |

---

## 文件迁移清单

- [ ] `agents/base/base_agent_loop.py` → `core/agent/simple/agent.py`
- [ ] `agents/base/basetool.py` → `core/tools/workspace.py`
- [ ] `agents/base/toolkit.py` → `core/tools/toolkit.py`
- [ ] `agents/providers/` → `core/providers/`
- [ ] 所有调用 BaseAgentLoop 的代码 → 使用 AgentFactory

---

## 新特性

### 1. 配置驱动创建
```python
# config.yaml
agent:
  type: "simple"
  id: "my_agent"
  model: "deepseek-chat"
  max_iterations: 10

# 代码
from core import bootstrap_agent
agent = await bootstrap_agent("config.yaml")
```

### 2. 运行时切换 SDK
```python
# 现在使用 SimpleAgent
agent = AgentFactory.create("simple", "my_agent")

# 未来切换到 LangGraph（只需要改这里）
agent = AgentFactory.create("langgraph", "my_agent")

# 其余代码完全一致！
```

### 3. 更好的类型支持
```python
from core.types import AgentMessage, AgentEvent, ToolResult

# 所有类型都有类型提示
async def handle_event(event: AgentEvent) -> None:
    ...
```

---

## 向后兼容

旧代码可以逐步迁移：

1. **阶段 1**: 保持旧代码运行
2. **阶段 2**: 新功能使用新架构
3. **阶段 3**: 逐步替换旧代码
4. **阶段 4**: 删除旧代码

旧代码中的 `BaseAgentLoop` 可以继续使用，同时逐步引入新架构。
