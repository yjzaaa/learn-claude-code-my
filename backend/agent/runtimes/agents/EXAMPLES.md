# Deep Agent 灵活构建器使用示例

## 快速开始

### 1. 基础用法 - 替换原来的 create_deep_agent

```python
from core.agent.runtimes.agents import AgentBuilder

# 创建带完整中间件栈的 Agent
agent = (
    AgentBuilder()
    .with_model("claude-sonnet-4-6")
    .with_tools([read_file, write_file, execute])
    .with_system_prompt("You are a helpful coding assistant")
    .with_backend(backend)
    .with_todo_list()
    .with_filesystem()
    .with_prompt_caching()
    .build()
)
```

### 2. 使用工厂函数快速创建

```python
from core.agent.runtimes.agents import (
    create_standard_agent,
    create_minimal_agent,
    create_agent_with_summarization,
)

# 标准 Agent（推荐）
agent = create_standard_agent(
    model="gpt-4",
    tools=tools,
    system_prompt="You are helpful",
    backend=backend,
)

# 最小化 Agent（资源受限场景）
agent = create_minimal_agent(
    model="claude-3-haiku",
    tools=tools,
    system_prompt="You are a calculator",
)

# 带压缩的 Agent（长会话）
agent = create_agent_with_summarization(
    model="claude-sonnet-4-6",
    tools=tools,
    backend=backend,
    trigger=("fraction", 0.85),  # 85% 时触发
    keep=("fraction", 0.10),     # 保留 10%
    with_manual_tool=True,       # 同时添加手动压缩工具
)
```

### 3. 使用 MiddlewareStack 灵活组合

```python
from core.agent.runtimes.agents import AgentBuilder, MiddlewareStack

# 定义可复用的中间件栈
standard_stack = (
    MiddlewareStack(backend=backend)
    .with_todo_list()
    .with_filesystem()
    .with_prompt_caching()
)

# 带压缩的栈
compression_stack = (
    MiddlewareStack(backend=backend)
    .with_todo_list()
    .with_filesystem()
    .with_summarization(
        trigger=("fraction", 0.85),
        keep=("fraction", 0.10),
        with_tool=True,  # 添加手动工具
    )
    .with_prompt_caching()
)

# 在多个 Agent 间复用
agent1 = (
    AgentBuilder()
    .with_model("gpt-4")
    .with_middleware_stack(standard_stack)
    .build()
)

agent2 = (
    AgentBuilder()
    .with_model("claude-sonnet-4-6")
    .with_middleware_stack(compression_stack)
    .build()
)
```

### 4. 条件组装（运行时决定中间件）

```python
builder = AgentBuilder()
builder.with_model("claude-sonnet-4-6")
builder.with_tools(tools)
builder.with_backend(backend)

# 基础中间件
builder.with_todo_list()
builder.with_filesystem()

# 条件添加
if enable_compression:
    builder.with_summarization(
        trigger=("fraction", 0.85),
        with_tool=True,
    )

if enable_human_approval:
    builder.with_human_in_the_loop(
        interrupt_on={"edit_file": True, "write_file": True}
    )

if skills:
    builder.with_skills_middleware(sources=skills)

agent = builder.build()
```

### 5. 添加自定义中间件

```python
from langchain.agents.middleware.types import AgentMiddleware

class MyCustomMiddleware(AgentMiddleware):
    def wrap_model_call(self, request, handler):
        # 自定义处理逻辑
        return handler(request)

# 方式1: 直接添加
agent = (
    AgentBuilder()
    .with_model("gpt-4")
    .with_todo_list()
    .add_middleware(MyCustomMiddleware())
    .build()
)

# 方式2: 使用 MiddlewareStack
stack = (
    MiddlewareStack()
    .with_todo_list()
    .add(MyCustomMiddleware())
)

agent = AgentBuilder().with_middleware_stack(stack).build()
```

### 6. 在 DeepRuntime 中启用压缩

```python
# 在 deep_runtime.py 的 _do_initialize 方法中

# 当前配置（无压缩）
builder = (
    AgentBuilder()
    .with_name(self._config.name or self._agent_id)
    .with_model(model)
    .with_tools(adapted_tools)
    .with_system_prompt(system_prompt)
    .with_backend(backend)
    .with_checkpointer(self._checkpointer)
    .with_store(self._store)
    .with_skills(self._config.skills or [])
    .with_todo_list()
    .with_filesystem()
    .with_prompt_caching()
)

# 启用压缩 - 取消注释并配置
builder = (
    AgentBuilder()
    .with_name(self._config.name or self._agent_id)
    .with_model(model)
    .with_tools(adapted_tools)
    .with_system_prompt(system_prompt)
    .with_backend(backend)
    .with_checkpointer(self._checkpointer)
    .with_store(self._store)
    .with_skills(self._config.skills or [])
    .with_todo_list()
    .with_filesystem()
    # 启用自动压缩
    .with_summarization(
        trigger=("fraction", 0.85),  # 85% 上下文窗口时触发
        keep=("fraction", 0.10),     # 保留最近 10%
        with_tool=True,              # 同时提供手动压缩工具
    )
    .with_prompt_caching()
)
```

### 7. 创建子 Agent

```python
# 创建子 Agent 配置
builder = (
    AgentBuilder()
    .with_model("claude-3-haiku")
    .with_tools([read_file])
    .with_system_prompt("You are a code reviewer")
    .with_todo_list()
)

# 生成子 Agent 规格
subagent_spec = builder.build_subagent(
    name="code_reviewer",
    description="Specialized in reviewing Python code",
)

# 在主 Agent 中使用
main_agent = (
    AgentBuilder()
    .with_model("gpt-4")
    .with_tools(tools)
    .with_subagents([subagent_spec])
    .build()
)
```

## 中间件栈顺序

构建后的中间件按以下顺序执行：

1. **TodoListMiddleware** - 任务规划
2. **MemoryMiddleware** - 记忆加载（可选）
3. **SkillsMiddleware** - 技能加载（可选）
4. **FilesystemMiddleware** - 文件操作
5. **SubAgentMiddleware** - 子 Agent（可选）
6. **SummarizationMiddleware** - 自动压缩（可选）
7. **SummarizationToolMiddleware** - 手动压缩工具（可选）
8. **AnthropicPromptCachingMiddleware** - 提示缓存
9. **自定义中间件**
10. **HumanInTheLoopMiddleware** - 人工介入（可选，最后）

## 配置选项

### 压缩中间件配置

```python
# 基于比例（推荐）
builder.with_summarization(
    trigger=("fraction", 0.85),  # 85% 上下文窗口时触发
    keep=("fraction", 0.10),     # 保留最近 10%
)

# 基于 Token 数
builder.with_summarization(
    trigger=("tokens", 100000),  # 100k tokens 时触发
    keep=("messages", 6),        # 保留最近 6 条消息
)

# 基于消息数
builder.with_summarization(
    trigger=("messages", 50),    # 50 条消息时触发
    keep=("messages", 10),       # 保留最近 10 条
)
```

### Human-in-the-Loop 配置

```python
builder.with_human_in_the_loop(
    interrupt_on={
        "edit_file": True,       # 编辑文件前暂停
        "write_file": True,      # 写入文件前暂停
        "execute": {             # 执行命令前暂停（复杂配置）
            "default": True,
            "exclude": ["ls", "pwd"],  # 排除这些命令
        },
    }
)
```

## 与原版 create_deep_agent 对比

| 特性 | create_deep_agent | AgentBuilder |
|------|-------------------|--------------|
| 灵活性 | 固定中间件栈 | 完全可配置 |
| 压缩中间件 | 默认启用 | 可选启用 |
| 手动压缩工具 | 不支持 | 支持 |
| 自定义中间件 | 困难 | 简单 |
| 子 Agent | 自动创建 | 显式控制 |
| 代码复杂度 | 低（黑盒） | 中（透明） |

## 调试技巧

```python
# 查看中间件栈
builder = AgentBuilder().with_todo_list().with_filesystem()
print(builder)
# 输出: AgentBuilder(model=None, middleware_stack=MiddlewareStack(middlewares=2))

# 克隆配置
builder2 = builder.clone()
builder2.with_summarization()  # 不影响 builder

# 逐步构建并检查
builder = AgentBuilder()
builder.with_model("gpt-4")
# ... 其他配置
agent = builder.build()
```
