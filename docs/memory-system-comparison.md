# 记忆系统对比分析

## 对比概述

| 维度 | Claude Code 记忆系统 | Deep Agent (deep_runtime.py) |
|------|---------------------|------------------------------|
| **架构类型** | 文件驱动 + 显式分类 | 状态驱动 + 隐式存储 |
| **存储介质** | Markdown 文件系统 | 内存 (InMemoryStore) + Checkpoint |
| **持久化层级** | 长期持久化 (磁盘) | 会话级持久化 (内存) |
| **记忆分类** | 四种显式类型 (user/feedback/project/reference) | 无显式分类，依赖对话状态 |
| **作用范围** | 跨会话、跨项目 | 单会话内 (通过 thread_id) |
| **用户可控性** | 高 (可直接编辑文件) | 低 (通过框架内部管理) |

---

## 详细对比

### 1. 存储架构

#### Claude Code
```
文件系统层次结构:
~/.claude/projects/
└── <project-slug>/
    ├── memory/
    │   ├── MEMORY.md          # 索引入口
    │   ├── user_*.md          # 用户记忆
    │   ├── feedback_*.md      # 反馈记忆
    │   ├── project_*.md       # 项目记忆
    │   └── reference_*.md     # 参考记忆
    └── team/                  # 团队记忆 (可选)
        └── MEMORY.md
```

**特点**:
- 显式文件存储，用户可直接查看和编辑
- 按项目隔离，按类型分类
- 支持版本控制 (git)
- 可通过文件系统工具 (grep/find) 搜索

#### Deep Agent
```python
# 代码中的存储组件
self._checkpointer = MemorySaver()   # LangGraph Checkpoint
self._store = InMemoryStore()        # 内存存储
self._dialogs = {}                   # 对话字典 {dialog_id: Dialog}
```

**特点**:
- 内存存储，进程结束即丢失
- 基于 LangGraph 的 checkpoint 机制
- 通过 `thread_id` 区分对话
- 支持流式状态恢复

---

### 2. 记忆类型系统

#### Claude Code - 显式四类型

| 类型 | 用途 | 范围 | 保存时机 |
|------|------|------|----------|
| **user** | 用户角色、目标、知识 | 私有 | 了解用户信息时 |
| **feedback** | 工作方式指导 | 默认私有 | 纠正或确认时 |
| **project** | 项目上下文 | 私有/团队 | 了解项目信息时 |
| **reference** | 外部系统指针 | 通常团队 | 发现外部资源时 |

**优势**:
- 结构化分类，便于检索
- 类型化指导，知道何时保存/使用
- 支持团队共享 (TEAMMEM)

#### Deep Agent - 隐式状态

无显式记忆类型，依赖以下机制:

```python
# 对话状态管理
dialog = Dialog(
    id=dialog_id,
    title=dialog_title,
    created_at=datetime.now(),
    updated_at=datetime.now()
)
dialog.add_human_message(user_input)
dialog.add_ai_message(accumulated_content, msg_id=message_id)
```

**特点**:
- 对话历史作为"记忆"
- 无显式分类，依赖 LLM 上下文
- 通过 checkpoint 恢复会话状态

---

### 3. 持久化机制

#### Claude Code - 长期持久化

```python
# 路径管理
getAutoMemPath() -> ~/.claude/projects/<slug>/memory/
getAutoMemEntrypoint() -> MEMORY.md

# 启用检查
isAutoMemoryEnabled():
  - CLAUDE_CODE_DISABLE_AUTO_MEMORY
  - CLAUDE_CODE_SIMPLE (--bare)
  - settings.autoMemoryEnabled
```

**持久化特性**:
- 写入磁盘，跨进程保留
- 项目级别隔离
- 支持团队同步 (TEAMMEM)
- 自动提取 (EXTRACT_MEMORIES) 后台代理

#### Deep Agent - 会话级持久化

```python
# 初始化存储
self._checkpointer = MemorySaver()  # 内存 checkpoint
self._store = InMemoryStore()       # 内存存储

# 对话配置
config = {
    "configurable": {"thread_id": dialog_id},
    "recursion_limit": 100
}
```

**持久化特性**:
- 内存存储，进程结束丢失
- 通过 `thread_id` 在同一会话中恢复
- 依赖 LangGraph 的 checkpoint 机制
- 无长期存储能力

---

### 4. 记忆提取与保存

#### Claude Code - 多方式提取

| 方式 | 触发条件 | 执行者 |
|------|----------|--------|
| **显式保存** | 用户说"记住" | 主代理 |
| **自动提取** | 对话结束 | 后台代理 (EXTRACT_MEMORIES) |
| **压缩提取** | 上下文满 | 压缩服务 |
| **技能审查** | /remember 命令 | remember 技能 |

**保存流程**:
```
识别记忆 -> 选择类型 -> 创建 .md 文件 -> 更新 MEMORY.md 索引
```

#### Deep Agent - 隐式保存

```python
# 流式处理中累积内容
accumulated_content = ""
async for raw_event in self._agent.astream(...):
    if content:
        accumulated_content += content
        
# 对话结束保存
dialog.add_ai_message(accumulated_content, msg_id=message_id)
```

**特点**:
- 对话内容自动累积
- 无显式记忆提取逻辑
- 依赖 LangGraph 内部状态管理

---

### 5. 记忆使用方式

#### Claude Code - 显式注入

```python
# 加载记忆到系统提示
async def loadMemoryPrompt() -> str:
    # 构建行为指南
    lines = buildMemoryLines('auto memory', autoMemDir)
    
    # 读取 MEMORY.md
    entrypointContent = fs.readFileSync(MEMORY.md)
    
    # 合并到系统提示
    return lines.join('\n') + entrypointContent
```

**使用特点**:
- 记忆作为系统提示的一部分
- 显式指导何时访问记忆
- 支持记忆漂移检测

#### Deep Agent - 隐式上下文

```python
# 通过 checkpoint 恢复状态
async for raw_event in self._agent.astream(
    {"messages": messages},
    config,  # 包含 thread_id
    stream_mode=["messages"]
):
    # 流式输出
```

**使用特点**:
- 通过 checkpoint 恢复对话状态
- 无显式记忆注入
- 依赖 LLM 的上下文窗口

---

### 6. 团队/共享记忆

#### Claude Code - TEAMMEM

```
团队记忆同步:
- watcher.ts: 文件监控
- teamMemPaths.ts: 团队路径管理
- secretScanner.ts: 敏感信息扫描
- 支持跨用户共享记忆
```

#### Deep Agent - 无内置支持

- 仅内存存储，无共享机制
- 需额外实现团队同步
- 可通过外部存储扩展

---

### 7. 配置与开关

#### Claude Code

| 配置项 | 类型 | 作用 |
|--------|------|------|
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | 环境变量 | 完全禁用记忆 |
| `CLAUDE_CODE_SIMPLE` | 环境变量 | 简化模式，禁用记忆 |
| `autoMemoryEnabled` | settings.json | 用户级别开关 |
| `autoMemoryDirectory` | settings.json | 自定义路径 |
| `EXTRACT_MEMORIES` | 功能标志 | 自动提取 |
| `TEAMMEM` | 功能标志 | 团队记忆 |

#### Deep Agent

```python
# 无显式记忆配置
# 依赖 LangGraph 内部配置
self._checkpointer = MemorySaver()
self._store = InMemoryStore()
```

---

## 优缺点对比

### Claude Code 记忆系统

**优点**:
- ✅ 长期持久化，跨会话保留
- ✅ 显式分类，结构化检索
- ✅ 用户可控，可直接编辑
- ✅ 支持团队共享
- ✅ 可版本控制
- ✅ 与文件系统工具集成 (grep/find)

**缺点**:
- ❌ 需要文件系统权限
- ❌ 需要显式管理 (索引更新)
- ❌ 可能产生文件碎片化
- ❌ 学习曲线较陡

### Deep Agent 记忆系统

**优点**:
- ✅ 简单易用，框架托管
- ✅ 实时状态恢复
- ✅ 与 LangGraph 深度集成
- ✅ 支持流式处理
- ✅ 无需文件系统管理

**缺点**:
- ❌ 无长期持久化 (进程结束丢失)
- ❌ 无显式记忆分类
- ❌ 用户无法直接查看/编辑
- ❌ 无团队共享机制
- ❌ 依赖上下文窗口

---

## 适用场景

| 场景 | 推荐系统 | 原因 |
|------|----------|------|
| 长期项目协作 | Claude Code | 需要跨会话保留上下文 |
| 团队协作 | Claude Code | TEAMMEM 支持共享 |
| 临时/单次任务 | Deep Agent | 简单，无需持久化 |
| 流式对话应用 | Deep Agent | 实时状态恢复 |
| 需要审计/版本控制 | Claude Code | 文件可版本化 |
| 快速原型 | Deep Agent | 配置简单 |

---

## 可能的融合方案

### 方案 1: Deep Agent + 文件持久化层

在 Deep Agent 基础上添加文件存储:

```python
class PersistentDeepAgentRuntime(DeepAgentRuntime):
    def __init__(self, agent_id: str, memory_dir: str):
        super().__init__(agent_id)
        self._file_store = FileBasedStore(memory_dir)  # 新增
        
    async def save_memory(self, memory_type: str, content: str):
        # 同时保存到内存和文件
        self._store.save(memory_type, content)
        await self._file_store.save(memory_type, content)
```

### 方案 2: Claude Code + LangGraph 运行时

用 LangGraph 替换 Claude Code 的执行引擎，保留文件记忆:

```python
# 保留文件记忆系统
from claude_code.memdir import loadMemoryPrompt

# 使用 LangGraph 运行时
from langgraph import create_react_agent

agent = create_react_agent(
    model,
    tools,
    checkpointer=MemorySaver(),
    # 注入文件记忆到系统提示
    system_prompt=loadMemoryPrompt() + base_system_prompt
)
```

### 方案 3: 混合架构

```
短期记忆 (Deep Agent 风格):
  - 对话上下文
  - 实时状态
  - 内存存储

长期记忆 (Claude Code 风格):
  - 用户偏好
  - 项目知识
  - 文件存储
```

---

## 总结

两个记忆系统代表了不同的设计理念:

- **Claude Code**: 工程化、显式、长期、可审计
- **Deep Agent**: 简洁、隐式、会话级、框架托管

选择取决于具体需求:
- 需要**长期协作** → Claude Code 模式
- 需要**快速部署** → Deep Agent 模式
- 需要**两全其美** → 考虑融合方案
