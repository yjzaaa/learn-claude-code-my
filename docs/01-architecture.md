# free-code 项目架构分析

## 1. 项目概述

### 1.1 项目定位
free-code 是一个类 Claude Code 的迷你 Agent 学习项目，是一个基于 TypeScript/Bun 构建的 CLI 工具，提供交互式 AI 编程助手功能。

### 1.2 主要功能
- **交互式 REPL**: 基于 Ink/React 的终端 UI，提供富交互体验
- **AI 对话**: 支持多轮对话，集成 Anthropic Claude API
- **工具系统**: 可扩展的工具调用机制（文件操作、命令执行、Agent 等）
- **命令系统**: 斜杠命令（/command）支持各种快捷操作
- **MCP 集成**: Model Context Protocol 支持，可连接外部服务
- **插件系统**: 支持加载和管理插件
- **技能系统**: 可复用的技能模块
- **Bridge 模式**: 远程控制和 IDE 集成
- **多模型支持**: 支持 Anthropic、OpenAI、AWS Bedrock、Google Vertex 等

### 1.3 技术栈

| 类别 | 技术 |
|------|------|
| 运行时 | Bun 1.3.11+ |
| 语言 | TypeScript 6.0.2 |
| UI 框架 | React 19 + Ink 6.8（终端 UI） |
| AI SDK | @anthropic-ai/sdk 0.80.0 |
| Agent SDK | @anthropic-ai/claude-agent-sdk 0.2.87 |
| MCP SDK | @modelcontextprotocol/sdk 1.29.0 |
| 构建工具 | Bun 内置 bundler |
| 状态管理 | 自定义 Store 模式（类 Zustand） |
| 配置管理 | 本地 JSON 文件 + 远程配置 |

---

## 2. 入口点分析

### 2.1 CLI 入口 (src/entrypoints/cli.tsx)

**文件统计**: 312 行

cli.tsx 是应用的引导入口点，采用动态导入策略优化启动性能：

```typescript
/**
 * Bootstrap entrypoint - checks for special flags before loading the full CLI.
 * All imports are dynamic to minimize module evaluation for fast paths.
 */
async function main(): Promise<void> {
  const args = process.argv.slice(2);

  // Fast-path for --version/-v: zero module loading needed
  if (args.length === 1 && (args[0] === '--version' || args[0] === '-v')) {
    console.log(`${MACRO.VERSION} (Claude Code)`);
    return;
  }
  // ... 其他快速路径
}
```

**主要快速路径**:
1. `--version` - 零模块加载，直接返回版本
2. `--dump-system-prompt` - 输出系统提示词
3. `--claude-in-chrome-mcp` - Chrome 扩展 MCP 服务器
4. `--chrome-native-host` - Chrome 原生主机模式
5. `--computer-use-mcp` - 计算机使用 MCP 服务器
6. `--daemon-worker` - 守护进程工作器
7. `remote-control/bridge` - 远程控制模式
8. `daemon` - 守护进程主程序
9. `ps/logs/attach/kill` - 后台会话管理
10. `new/list/reply` - 模板任务命令
11. `--worktree --tmux` - Tmux 工作区模式

### 2.2 初始化入口 (src/entrypoints/init.ts)

**文件统计**: 8,632 行

负责应用初始化：
- 配置加载和验证
- 认证初始化（OAuth/API Key）
- 遥测和分析初始化
- 设置迁移
- 策略限制加载

---

## 3. 核心引擎

### 3.1 QueryEngine (src/QueryEngine.ts)

**文件统计**: 1,295 行

QueryEngine 是查询生命周期和会话状态的管理类：

```typescript
export class QueryEngine {
  private config: QueryEngineConfig
  private mutableMessages: Message[]
  private abortController: AbortController
  private permissionDenials: SDKPermissionDenial[]
  private totalUsage: NonNullableUsage
  private readFileState: FileStateCache
  private discoveredSkillNames = new Set<string>()
  private loadedNestedMemoryPaths = new Set<string>()

  async *submitMessage(
    prompt: string | ContentBlockParam[],
    options?: { uuid?: string; isMeta?: boolean },
  ): AsyncGenerator<SDKMessage, void, unknown> {
    // 处理用户输入，生成 AI 响应
  }
}
```

**核心职责**:
- 管理对话消息状态
- 处理用户输入并生成 AI 响应
- 工具调用协调
- 权限拒绝跟踪
- 文件状态缓存管理
- 技能发现跟踪

**配置结构**:
```typescript
export type QueryEngineConfig = {
  cwd: string
  tools: Tools
  commands: Command[]
  mcpClients: MCPServerConnection[]
  agents: AgentDefinition[]
  canUseTool: CanUseToolFn
  getAppState: () => AppState
  setAppState: (f: (prev: AppState) => AppState) => void
  initialMessages?: Message[]
  readFileCache: FileStateCache
  customSystemPrompt?: string
  // ... 其他配置
}
```

### 3.2 Query 处理 (src/query.ts)

**文件统计**: 1,729 行

query.ts 包含核心的查询循环逻辑：

```typescript
export type QueryParams = {
  messages: Message[]
  systemPrompt: SystemPrompt
  userContext: { [k: string]: string }
  systemContext: { [k: string]: string }
  canUseTool: CanUseToolFn
  toolUseContext: ToolUseContext
  fallbackModel?: string
  querySource: QuerySource
  maxOutputTokensOverride?: number
  maxTurns?: number
  skipCacheWrite?: boolean
  taskBudget?: { total: number }
  deps?: QueryDeps
}

export async function* query(
  params: QueryParams,
): AsyncGenerator<StreamEvent | RequestStartEvent | Message | TombstoneMessage | ToolUseSummaryMessage, Terminal> {
  const consumedCommandUuids: string[] = []
  const terminal = yield* queryLoop(params, consumedCommandUuids)
  // 通知命令生命周期完成
  for (const uuid of consumedCommandUuids) {
    notifyCommandLifecycle(uuid, 'completed')
  }
  return terminal
}
```

**查询循环状态**:
```typescript
type State = {
  messages: Message[]
  toolUseContext: ToolUseContext
  autoCompactTracking: AutoCompactTrackingState | undefined
  maxOutputTokensRecoveryCount: number
  hasAttemptedReactiveCompact: boolean
  maxOutputTokensOverride: number | undefined
  pendingToolUseSummary: Promise<ToolUseSummaryMessage | null> | undefined
  stopHookActive: boolean | undefined
  turnCount: number
  transition: Continue | undefined
}
```

**主要功能**:
- 消息流生成器模式
- 自动压缩跟踪
- Token 预算管理
- 工具执行编排
- 停止钩子处理
- 错误恢复机制

---

## 4. 主应用逻辑 (src/main.tsx)

**文件统计**: 4,684 行

main.tsx 是应用的主逻辑入口，包含 Commander CLI 配置和主循环：

### 4.1 启动流程

```typescript
// 启动性能分析
profileCheckpoint('main_tsx_entry');

// 并行初始化
startMdmRawRead();      // MDM 设置读取
startKeychainPrefetch(); // 钥匙串预取

// 主要初始化
await init();  // 配置、认证、遥测初始化
await initializeTelemetryAfterTrust();
```

### 4.2 CLI 命令结构

```typescript
const program = new CommanderCommand()
  .name('claude')
  .version(MACRO.VERSION)
  .option('-p, --print', 'print the response')
  .option('--dangerously-skip-permissions', 'skip permission prompts')
  .option('-m, --model <model>', 'model to use')
  .option('--verbose', 'enable verbose logging')
  // ... 更多选项
```

### 4.3 主循环模式

1. **交互模式**: 启动 REPL TUI
2. **Headless 模式**: `-p` 参数，单次查询
3. **远程模式**: 连接到远程会话
4. **助手模式**: AI 助手功能

---

## 5. 数据流

### 5.1 完整数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           用户输入                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     src/entrypoints/cli.tsx                              │
│                     (CLI 入口/快速路径分发)                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     src/main.tsx                                         │
│                     (命令解析/初始化/模式分发)                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌──────────┐     ┌──────────┐    ┌──────────┐
            │ 交互模式  │     │Headless  │    │ 远程模式  │
            │ (REPL)   │     │ 模式     │    │          │
            └────┬─────┘     └────┬─────┘    └────┬─────┘
                 │                │               │
                 ▼                ▼               ▼
            ┌──────────────────────────────────────────┐
            │      src/QueryEngine.ts                  │
            │      (查询生命周期管理)                    │
            └──────────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────────┐
            │      src/query.ts                         │
            │      (查询循环/消息流生成器)                │
            └──────────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │  LLM API    │    │   工具执行   │    │  状态更新   │
    │  调用       │    │  (Tools)    │    │             │
    └─────────────┘    └─────────────┘    └─────────────┘
           │                   │                   │
           └───────────────────┼───────────────────┘
                               ▼
            ┌──────────────────────────────────────────┐
            │      src/state/AppState.tsx              │
            │      (状态管理/通知订阅)                  │
            └──────────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────────┐
            │      UI 组件 (Ink/React)                 │
            │      (终端渲染)                          │
            └──────────────────────────────────────────┘
```

### 5.2 消息流详细流程

```
用户输入
    │
    ▼
┌─────────────────┐
│ processUserInput │  (src/utils/processUserInput/)
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ QueryEngine.    │
│ submitMessage() │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ query() 生成器   │
│ 函数            │
└─────────────────┘
    │
    ├──► 构建系统提示词 (fetchSystemPromptParts)
    │
    ├──► 调用 LLM API ( Anthropic/OpenAI/etc )
    │
    ├──► 流式响应处理
    │
    ├──► 工具调用检测
    │         │
    │         ▼
    │    ┌─────────────┐
    │    │ 工具权限检查 │
    │    │ canUseTool  │
    │    └─────────────┘
    │         │
    │         ▼
    │    ┌─────────────┐
    │    │ 工具执行    │
    │    │ runTools    │
    │    └─────────────┘
    │         │
    │         ▼
    │    工具结果返回 ─────┐
    │                      │
    │◄─────────────────────┘
    │
    ▼
┌─────────────────┐
│ 消息持久化      │
│ (sessionStorage)│
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ UI 更新         │
│ (Ink 渲染)      │
└─────────────────┘
```

---

## 6. 状态管理

### 6.1 状态架构

状态管理采用自定义 Store 模式（类似 Zustand）：

```
src/state/
├── AppState.tsx          (199 行) - React 上下文提供者
├── AppStateStore.ts      (569 行) - 状态类型定义和默认值
├── onChangeAppState.ts   (状态变更处理)
├── selectors.ts          (状态选择器)
├── store.ts              (Store 实现)
└── teammateViewHelpers.ts(队友视图辅助)
```

### 6.2 AppState 结构

```typescript
export type AppState = DeepImmutable<{
  // 设置
  settings: SettingsJson
  verbose: boolean
  mainLoopModel: ModelSetting
  mainLoopModelForSession: ModelSetting
  statusLineText: string | undefined
  
  // UI 状态
  expandedView: 'none' | 'tasks' | 'teammates'
  isBriefOnly: boolean
  selectedIPAgentIndex: number
  coordinatorTaskIndex: number
  viewSelectionMode: 'none' | 'selecting-agent' | 'viewing-agent'
  footerSelection: FooterItem | null
  
  // 工具权限
  toolPermissionContext: ToolPermissionContext
  
  // Agent/助手
  agent: string | undefined
  kairosEnabled: boolean
  
  // 远程/Bridge
  remoteSessionUrl: string | undefined
  remoteConnectionStatus: 'connecting' | 'connected' | 'reconnecting' | 'disconnected'
  remoteBackgroundTaskCount: number
  replBridgeEnabled: boolean
  replBridgeConnected: boolean
  replBridgeSessionActive: boolean
  // ... 更多 bridge 状态
  
  // MCP
  mcp: {
    clients: MCPServerConnection[]
    tools: Tool[]
    commands: Command[]
    resources: Record<string, ServerResource[]>
    pluginReconnectKey: number
  }
  
  // 插件
  plugins: {
    enabled: LoadedPlugin[]
    disabled: LoadedPlugin[]
    commands: Command[]
    errors: PluginError[]
    installationStatus: { ... }
  }
  
  // 任务
  tasks: { [taskId: string]: TaskState }
  agentNameRegistry: Map<string, AgentId>
  foregroundedTaskId?: string
  viewingAgentTaskId?: string
  
  // 其他...
}>
```

### 6.3 Store 实现

```typescript
// src/state/store.ts
export type Store<T> = {
  getState: () => T
  setState: (updater: (prev: T) => T) => void
  subscribe: (callback: () => void) => () => void
}

export function createStore<T>(
  initialState: T,
  onChange?: (args: { newState: T; oldState: T }) => void,
): Store<T> {
  let state = initialState
  const listeners = new Set<() => void>()
  
  return {
    getState: () => state,
    setState: (updater) => {
      const oldState = state
      state = updater(state)
      if (onChange) onChange({ newState: state, oldState })
      listeners.forEach(cb => cb())
    },
    subscribe: (cb) => {
      listeners.add(cb)
      return () => listeners.delete(cb)
    },
  }
}
```

### 6.4 React Hooks

```typescript
// 订阅状态切片
export function useAppState<T>(selector: (state: AppState) => T): T {
  const store = useAppStore()
  const get = () => selector(store.getState())
  return useSyncExternalStore(store.subscribe, get, get)
}

// 获取 setState
export function useSetAppState() {
  return useAppStore().setState
}

// 获取整个 store
export function useAppStateStore() {
  return useAppStore()
}
```

---

## 7. 架构图

### 7.1 模块关系图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              表现层 (Presentation)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  REPL.tsx   │  │  命令组件   │  │  对话框组件  │  │   其他 UI 组件      │ │
│  │  (主屏幕)   │  │             │  │             │  │                     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         └─────────────────┴─────────────────┘                    │            │
│                                   │                              │            │
│                                   ▼                              ▼            │
│                         ┌─────────────────────┐      ┌─────────────────────┐  │
│                         │   AppState.tsx      │      │   components/       │  │
│                         │   (状态管理)         │      │   (通用组件)         │  │
│                         └─────────────────────┘      └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              应用层 (Application)                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        main.tsx (CLI/命令解析)                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────┐  ┌─────────────────────────────────────────────┐│
│  │    QueryEngine.ts       │  │         query.ts (查询循环)                  ││
│  │    (查询生命周期管理)    │  │                                             ││
│  └─────────────────────────┘  └─────────────────────────────────────────────┘│
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌────────────────┐│
│  │    commands.ts          │  │      tools.ts           │  │   hooks/       ││
│  │    (命令注册表)          │  │    (工具注册表)          │  │   (React Hooks)││
│  └─────────────────────────┘  └─────────────────────────┘  └────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              领域层 (Domain)                                 │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌────────────────┐│
│  │      Tool.ts            │  │      Task.ts            │  │   types/       ││
│  │    (工具类型定义)        │  │    (任务类型定义)        │  │   (类型定义)    ││
│  └─────────────────────────┘  └─────────────────────────┘  └────────────────┘│
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌────────────────┐│
│  │    commands/            │  │      tools/             │  │   skills/      ││
│  │    (命令实现)            │  │    (工具实现)            │  │   (技能实现)    ││
│  └─────────────────────────┘  └─────────────────────────┘  └────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            基础设施层 (Infrastructure)                        │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌────────────────┐│
│  │     services/           │  │       utils/            │  │   bridge/      ││
│  │   (API/认证/分析服务)    │  │     (工具函数)           │  │   (IDE 桥接)    ││
│  └─────────────────────────┘  └─────────────────────────┘  └────────────────┘│
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌────────────────┐│
│  │     plugins/            │  │      tasks/             │  │   voice/       ││
│  │    (插件系统)            │  │    (后台任务)            │  │   (语音输入)    ││
│  └─────────────────────────┘  └─────────────────────────┘  └────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 核心类/模块依赖图

```
┌─────────────────────────────────────────────────────────────────┐
│                        cli.tsx                                  │
│                    (入口点/引导)                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        main.tsx                                 │
│                   (CLI 配置/主循环)                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   QueryEngine   │  │    commands/    │  │     tools/      │
│                 │  │                 │  │                 │
│ ┌─────────────┐ │  │ 命令注册和执行  │  │ 工具注册和执行  │
│ │  submitMsg  │ │  └─────────────────┘  └─────────────────┘
│ └──────┬──────┘ │           │                   │
└────────┼────────┘           │                   │
         │                    │                   │
         ▼                    │                   │
┌─────────────────┐           │                   │
│    query.ts     │◄──────────┴───────────────────┘
│                 │         (通过参数传递)
│ ┌─────────────┐ │
│ │ queryLoop   │ │
│ │ (生成器函数) │ │
│ └──────┬──────┘ │
└────────┼────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│              services/api/                        │
│         (LLM API 调用/流式处理)                    │
└──────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│           services/tools/                         │
│           (工具执行编排)                           │
└──────────────────────────────────────────────────┘
```

---

## 8. 项目统计

### 8.1 文件统计

| 目录 | 文件数 | 说明 |
|------|--------|------|
| src/ | 1,914 个 TS/TSX 文件 | 源代码 |
| src/commands/ | ~50+ | 命令实现 |
| src/tools/ | ~30+ | 工具实现 |
| src/components/ | ~40+ | UI 组件 |
| src/services/ | ~100+ | 服务层 |
| src/utils/ | ~200+ | 工具函数 |
| src/hooks/ | ~30+ | React Hooks |

### 8.2 核心文件行数

| 文件 | 行数 | 说明 |
|------|------|------|
| src/main.tsx | 4,684 | 主应用逻辑 |
| src/query.ts | 1,729 | 查询循环 |
| src/QueryEngine.ts | 1,295 | 查询引擎 |
| src/interactiveHelpers.tsx | 57,424 | 交互辅助函数 |
| src/entrypoints/cli.tsx | 312 | CLI 入口 |
| src/state/AppState.tsx | 199 | 状态管理 React 层 |
| src/state/AppStateStore.ts | 569 | 状态类型定义 |
| src/Tool.ts | 29,516 | 工具类型定义 |
| src/commands.ts | 25,185 | 命令注册表 |
| src/tools.ts | 17,294 | 工具注册表 |

### 8.3 总代码量

- **总 TypeScript 文件数**: 1,914 个
- **总代码行数**: ~48,330 行

---

## 9. 关键设计模式

### 9.1 生成器模式 (Generator Pattern)

query.ts 使用 AsyncGenerator 实现流式消息处理：

```typescript
export async function* query(params: QueryParams): AsyncGenerator<...> {
  // 产生流事件、消息、工具结果等
  yield event
}
```

### 9.2 依赖注入

QueryEngine 通过配置对象注入依赖：

```typescript
export type QueryEngineConfig = {
  canUseTool: CanUseToolFn
  getAppState: () => AppState
  setAppState: (f: (prev: AppState) => AppState) => void
  // ...
}
```

### 9.3 特征标志 (Feature Flags)

使用 `feature()` 函数进行编译时死代码消除：

```typescript
const voiceCommand = feature('VOICE_MODE')
  ? require('./commands/voice/index.js').default
  : null
```

### 9.4 动态导入

优化启动性能，按需加载模块：

```typescript
const { profileCheckpoint } = await import('../utils/startupProfiler.js')
```

---

## 10. 扩展点

### 10.1 添加新命令

1. 在 `src/commands/` 创建命令目录
2. 实现命令逻辑
3. 在 `src/commands.ts` 注册

### 10.2 添加新工具

1. 在 `src/tools/` 创建工具目录
2. 实现工具类（实现 Tool 接口）
3. 在 `src/tools.ts` 注册

### 10.3 添加新技能

1. 在 `src/skills/` 创建技能
2. 实现技能逻辑
3. 在 `src/skills/bundled/index.ts` 注册

---

*文档生成时间: 2026-04-06*
*分析项目: free-code-main (Claude Code 源码快照)*
