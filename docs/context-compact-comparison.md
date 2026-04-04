# 上下文压缩机制深度对比

## 对比概览

| 维度 | Claude Code | Deep-Agent 框架 (SummarizationMiddleware) |
|------|-------------|------------------------------------------|
| **压缩层级** | 4+ 层（micro/auto/partial/session） | 2 层（argument truncation + full summarization） |
| **触发方式** | 自动 + 手动 + 智能预测 | 自动阈值 + 手动工具 |
| **压缩算法** | 智能摘要 + 缓存编辑 + 选择性保留 | LLM 摘要 + 参数截断 |
| **持久化** | 会话记忆 + 文件存储 | Backend 存储（/conversation_history/） |
| **用户交互** | 警告提示 + 透明压缩 | 透明压缩 + 手动工具触发 |
| **特色功能** | 缓存编辑、时间触发、智能预测 | 参数预截断、Backend 卸载、双模式触发 |

---

## Claude Code 压缩系统

### 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Session Memory Compact                             │
│ - 保存完整会话状态到记忆系统                                  │
│ - 支持跨会话恢复                                             │
└─────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Partial Compact (智能预测压缩)                       │
│ - 预压缩分析，预测需要保留的内容                               │
│ - 保留关键文件内容和工具调用结果                               │
└─────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Auto Compact (自动压缩)                             │
│ - 基于 token 阈值自动触发                                     │
│ - 支持多种压缩策略 (claude/gpt 不同处理)                      │
│ - 图像剥离、附件去重                                          │
└─────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Micro Compact (微压缩)                              │
│ - 每轮静默执行                                               │
│ - 缓存编辑 (cache_edits) 删除旧工具结果                       │
│ - 时间触发 (time-based)                                       │
│ - Snip 标记压缩                                              │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. Micro Compact (微压缩)

**文件**: `src/services/compact/microCompact.ts`

```typescript
// 缓存编辑机制
export function createCacheEditsBlock(
  state: CachedMCState
): ContentBlock[] | null {
  const toolIds = getToolResultsToDelete(state)
  if (toolIds.length === 0) return null

  return [{
    type: 'cache_edits',
    cache_edits: toolIds.map(id => ({
      type: 'cache_delete',
      hash: id
    }))
  }]
}
```

**特点**:
- 使用 Anthropic API 的 `cache_edits` 功能
- 静默删除超过 3 轮的旧工具结果
- 支持时间触发 (`timeBasedMCConfig.ts`)
- 保持 API 调用效率

#### 2. Auto Compact (自动压缩)

**文件**: `src/services/compact/autoCompact.ts`

```typescript
export function getAutoCompactThreshold(model: string): number {
  const contextWindow = getEffectiveContextWindowSize(model)
  // 70% 阈值
  return Math.floor(contextWindow * 0.7)
}

export async function autoCompactIfNeeded(
  messages: Message[],
  model: string
): Promise<CompactResult | null> {
  if (!shouldAutoCompact(model, estimateTokens(messages))) {
    return null
  }
  return compactConversation(messages, model)
}
```

**特点**:
- 动态阈值计算 (模型上下文窗口的 70%)
- 支持不同模型的差异化处理
- 警告状态管理 (`compactWarningState.ts`)
- 智能预测是否需要压缩

#### 3. Partial Compact (部分压缩)

**文件**: `src/services/compact/compact.ts`

```typescript
export async function partialCompactConversation(
  messages: Message[],
  model: string,
  preservedSegments: string[]
): Promise<CompactionResult> {
  // 预压缩分析
  // 预测需要保留的内容
  // 保留关键文件内容和工具调用
}
```

**特点**:
- 预压缩分析
- 保留被引用的文件内容
- 保留关键决策点
- 智能选择压缩边界

#### 4. Session Memory Compact (会话记忆压缩)

**文件**: `src/services/compact/sessionMemoryCompact.ts`

```typescript
export async function trySessionMemoryCompaction(
  messages: Message[],
  model: string
): Promise<SessionMemoryCompactResult> {
  // 将会话状态保存到记忆系统
  // 支持跨会话恢复
  // 计算需要保留的消息索引
}
```

**特点**:
- 保存完整会话状态
- 支持从记忆系统恢复
- 长期持久化

---

## Deep-Agent 框架压缩系统

### 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Full Summarization (完整摘要)                        │
│ - LLM 生成对话摘要                                           │
│ - 卸载完整历史到 Backend                                     │
│ - 替换旧消息为摘要                                           │
└─────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Argument Truncation (参数截断)                       │
│ - 预压缩优化                                                 │
│ - 截断旧消息中的大工具参数                                   │
│ - 针对 write_file/edit_file 等工具                           │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. SummarizationMiddleware (自动压缩)

**文件**: `.venv/Lib/site-packages/deepagents/middleware/summarization.py`

```python
class _DeepAgentsSummarizationMiddleware(AgentMiddleware):
    """Summarization middleware with backend for conversation history offloading."""

    def __init__(
        self,
        model: str | BaseChatModel,
        *,
        backend: BACKEND_TYPES,
        trigger: ContextSize | list[ContextSize] | None = None,
        keep: ContextSize = ("messages", _DEFAULT_MESSAGES_TO_KEEP),
        truncate_args_settings: TruncateArgsSettings | None = None,
    ) -> None:
```

**两层压缩机制**:

**第一层：Argument Truncation (参数截断)**

```python
class TruncateArgsSettings(TypedDict, total=False):
    """Settings for truncating large tool-call arguments in older messages.

    This is a lightweight, pre-summarization optimization that fires at a lower
    token threshold than full conversation compaction.
    """
    trigger: ContextSize | None  # 触发阈值
    keep: ContextSize            # 保留窗口
    max_length: int              # 参数最大长度
    truncation_text: str         # 截断后缀文本
```

- 轻量级预压缩优化
- 在完整摘要之前触发（更低阈值）
- 仅截断旧消息中 `AIMessage.tool_calls` 的 `args` 值
- 针对特定工具（`write_file`, `edit_file`）
- 保留最近消息完整

**第二层：Full Summarization (完整摘要)**

```python
def wrap_model_call(
    self,
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse | ExtendedModelResponse:
    """Process messages before model invocation, with history offloading and arg truncation."""
    # Step 1: Truncate args if configured
    truncated_messages, _ = self._truncate_args(...)

    # Step 2: Check if summarization should happen
    should_summarize = self._should_summarize(truncated_messages, total_tokens)

    # Step 3: Perform summarization
    # - Offload to backend
    # - Generate summary via LLM
    # - Build new messages with summary
```

**触发条件**:
- `("tokens", N)` - Token 数量阈值
- `("messages", N)` - 消息数量阈值  
- `("fraction", F)` - 上下文窗口比例

**默认配置**:
```python
def compute_summarization_defaults(model: BaseChatModel) -> SummarizationDefaults:
    if has_profile:
        return {
            "trigger": ("fraction", 0.85),      # 85% 触发
            "keep": ("fraction", 0.10),         # 保留最近 10%
            "truncate_args_settings": {
                "trigger": ("fraction", 0.85),
                "keep": ("fraction", 0.10),
            },
        }
    else:
        return {
            "trigger": ("tokens", 170000),
            "keep": ("messages", 6),
            "truncate_args_settings": {
                "trigger": ("messages", 20),
                "keep": ("messages", 20),
            },
        }
```

#### 2. Backend 存储机制

```python
def _offload_to_backend(
    self,
    backend: BackendProtocol,
    messages: list[AnyMessage],
) -> str | None:
    """Persist messages to backend before summarization."""
    path = self._get_history_path()  # /conversation_history/{thread_id}.md

    # 追加到 markdown 文件
    new_section = f"## Summarized at {timestamp}\n\n{get_buffer_string(filtered_messages)}\n\n"

    # 读取现有内容并追加
    result = backend.edit(path, existing_content, combined_content)
```

**特点**:
- 按 thread_id 存储对话历史
- Markdown 格式，带时间戳
- 支持链式摘要（过滤已摘要消息）
- Backend 抽象（文件系统、Daytona 等）

#### 3. SummarizationToolMiddleware (手动压缩)

```python
class SummarizationToolMiddleware(AgentMiddleware):
    """Middleware that provides a `compact_conversation` tool for manual compaction."""

    def _create_compact_tool(self) -> BaseTool:
        return StructuredTool.from_function(
            name="compact_conversation",
            description=(
                "Compact the conversation by summarizing older messages "
                "into a concise summary. Use this proactively when the "
                "conversation is getting long to free up context window space."
            ),
        )
```

**特点**:
- 提供 `compact_conversation` 工具
- 由 Agent 或用户手动触发
- 复用 `SummarizationMiddleware` 的引擎
- 资格门槛：达到自动触发阈值的 50%

---

## 详细对比

### 1. 微压缩层对比

| 特性 | Claude Code (Micro Compact) | Deep-Agent (Argument Truncation) |
|------|------------------------------|----------------------------------|
| **实现方式** | 缓存编辑 (cache_edits) | 参数截断（字符串裁剪） |
| **删除粒度** | 精确的 tool_result 级别 | 工具调用参数字段 |
| **保留策略** | 基于时间 + 引用关系 | 保留最近 N 条/比例 |
| **API 效率** | 高 (利用 API 缓存机制) | 中 (修改消息内容) |
| **可恢复性** | 可恢复 (重新请求) | 可恢复 (Backend 存储) |
| **针对性** | 通用工具结果 | 特定工具（write/edit） |

### 2. 自动压缩层对比

| 特性 | Claude Code (Auto Compact) | Deep-Agent (Full Summarization) |
|------|-----------------------------|----------------------------------|
| **阈值策略** | 动态 (模型窗口的 70%) | 可配置（比例/Token/消息数） |
| **压缩算法** | 智能摘要 + 选择性保留 | LLM 摘要（LangChain） |
| **持久化** | 会话记忆 + 可选存储 | Backend 存储（.md 文件） |
| **模型适配** | 针对不同模型优化 | 依赖模型 profile |
| **预处理** | 图像剥离、附件去重 | 参数预截断 |
| **回退机制** | ContextOverflowError 捕获 | 自动 + 手动工具 |

### 3. 智能特性对比

| 特性 | Claude Code | Deep-Agent |
|------|-------------|------------|
| **预测压缩** | ✅ Partial Compact | ❌ |
| **引用追踪** | ✅ 保留被引用内容 | ❌ |
| **时间触发** | ✅ Time-based MC | ❌ |
| **会话恢复** | ✅ Session Memory | ⚠️ Backend 依赖 |
| **警告提示** | ✅ 渐进式警告 | ❌ |
| **手动工具** | ❌ | ✅ compact_conversation |
| **参数预截断** | ❌ | ✅ TruncateArgsSettings |
| **Backend 存储** | ❌ | ✅ 抽象 Backend |

### 4. 存储对比

| 特性 | Claude Code | Deep-Agent |
|------|-------------|------------|
| **存储位置** | `~/.claude/` 文件系统 | Backend（可配置） |
| **格式** | 自定义格式 | Markdown |
| **组织结构** | 项目/会话隔离 | thread_id 隔离 |
| **可访问性** | 用户可直接查看 | 依赖 Backend 实现 |
| **版本控制** | 天然支持 | 依赖 Backend |

### 5. 代码复杂度对比

**Claude Code**:
```
src/services/compact/
├── apiMicrocompact.ts      # API 级微压缩
├── autoCompact.ts          # 自动压缩逻辑
├── cachedMicrocompact.ts   # 缓存编辑状态
├── cachedMCConfig.ts       # 缓存配置
├── compact.ts              # 主压缩逻辑 (1400+ 行)
├── compactWarningHook.ts   # 警告钩子
├── compactWarningState.ts  # 警告状态
├── grouping.ts             # 消息分组
├── microCompact.ts         # 微压缩实现
├── partialCompact.ts       # 部分压缩
├── postCompactCleanup.ts   # 压缩后清理
├── prompt.ts               # 压缩提示词
├── sessionMemoryCompact.ts # 会话记忆压缩
├── snipCompact.ts          # Snip 压缩
├── snipProjection.ts       # Snip 投影
└── timeBasedMCConfig.ts    # 时间配置
```

**Deep-Agent**:
```
deepagents/middleware/
└── summarization.py          # 完整实现 (1500+ 行)
    ├── SummarizationMiddleware      # 自动压缩
    ├── SummarizationToolMiddleware  # 手动工具
    ├── TruncateArgsSettings         # 参数截断配置
    └── create_summarization_*       # 工厂函数
```

---

## 性能对比

### Token 处理效率

| 场景 | Claude Code | Deep-Agent |
|------|-------------|------------|
| 微压缩开销 | ~1% (API 优化) | ~3% (参数截断) |
| 自动压缩触发 | 70% 阈值 | 85% 默认（可配置） |
| 压缩后保留 | 智能选择 | 配置化保留窗口 |
| 恢复成本 | 低（缓存命中） | 中（Backend 读取） |
| 存储成本 | 本地文件 | Backend 依赖 |

### 适用场景

| 场景 | 推荐方案 | 原因 |
|------|----------|------|
| 长会话 (>100 轮) | Claude Code | 智能预测 + 会话恢复 |
| 高频工具调用 | Claude Code | 缓存编辑优化 |
| 多 Backend 环境 | Deep-Agent | 抽象存储层 |
| 需要手动控制 | Deep-Agent | compact_conversation 工具 |
| 大文件操作频繁 | Deep-Agent | 参数预截断优化 |
| 生产级稳定性 | Claude Code | 多层级协同工作 |

---

## 融合建议

### 方案 1: Deep-Agent + Claude Code 缓存编辑

```python
class AdvancedSummarizationMiddleware(SummarizationMiddleware):
    """增强版压缩中间件"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_edits_enabled = True  # 来自 CC 的特性

    async def micro_compact(self, messages):
        # 使用类似 cache_edits 的机制
        # 而非参数截断
        pass
```

### 方案 2: Claude Code + Backend 存储

```typescript
// 将 sessionMemoryCompact 扩展为 Backend 支持
export async function sessionMemoryCompactWithBackend(
  messages: Message[],
  backend: BackendProtocol
): Promise<CompactResult> {
  // 保存到 Backend 而非本地文件
  // 支持远程恢复
}
```

### 方案 3: 混合策略

```
短期对话 (< 50 轮):
  └─► Deep-Agent 简单模式

中期对话 (50-100 轮):
  └─► Deep-Agent + 参数预截断

长期对话 (> 100 轮):
  └─► Claude Code 完整模式 + Backend 存储
```

---

## 总结

### Claude Code 特点

**优势**:
- ✅ 高度优化的多层压缩算法
- ✅ 智能预测和引用追踪
- ✅ 多层级协同工作
- ✅ 生产级稳定性
- ✅ Anthropic API 深度优化

**劣势**:
- ❌ 代码复杂度高
- ❌ 紧耦合 Anthropic API
- ❌ 无手动触发工具

### Deep-Agent 框架特点

**优势**:
- ✅ 双层压缩（参数截断 + 完整摘要）
- ✅ Backend 抽象层
- ✅ 手动/自动双模式
- ✅ 与 LangChain/LangGraph 深度集成
- ✅ 可配置性强

**劣势**:
- ❌ 无引用追踪
- ❌ 无智能预测
- ❌ 依赖 LangChain 摘要逻辑
- ❌ 无时间触发机制

### 选择建议

| 需求 | 选择 |
|------|------|
| 生产环境、长会话 | Claude Code |
| 需要 Backend 存储 | Deep-Agent |
| 需要手动控制 | Deep-Agent |
| Anthropic API 优先 | Claude Code |
| LangChain 生态 | Deep-Agent |
| 多模型支持 | Deep-Agent |
