# Claude Code 工具与命令系统分析

## 概述

本文档分析 free-code-main 项目（Claude Code 参考实现）的工具（Tools）和命令（Commands）系统架构。该系统采用模块化设计，支持动态加载、权限控制和扩展机制。

---

## 一、工具系统（Tool System）

### 1.1 工具注册机制

工具注册位于 `src/tools.ts`，采用集中式注册表模式：

```typescript
// 核心函数
export function getAllBaseTools(): Tool[]  // 获取所有基础工具
export function getTools(options: GetToolsOptions): Tool[]  // 根据条件筛选工具
export function assembleToolPool(params: ToolPoolParams): Promise<ToolDefinition[]>  // 组装工具池
```

**注册流程：**
1. 基础工具在 `tools.ts` 中静态导入
2. 条件工具通过 `isEnabled()` 动态控制
3. 外部工具（MCP）动态加载并合并

### 1.2 工具类型定义

核心工具接口位于 `src/Tool.ts`：

```typescript
export interface Tool {
  name: string                    // 工具名称
  description(): string           // 工具描述（动态生成）
  prompt(): string | undefined    // 使用提示

  // 执行控制
  call(params: string, context: ToolUseContext): Promise<ToolResult>
  isEnabled(): boolean
  isReadOnly(): boolean
  isConcurrencySafe(): boolean

  // 权限控制
  checkPermissions(params: string, context: ToolUseContext): Promise<PermissionCheckResult>

  // UI 渲染
  render?(params: string, context: ToolUseContext): React.ReactNode
  renderResult?(params: string, result: ToolResult, context: ToolUseContext): React.ReactNode
}
```

### 1.3 工具分类列表

#### 文件操作工具
| 工具名 | 文件路径 | 功能描述 |
|--------|----------|----------|
| `Read` | `src/tools/FileReadTool/FileReadTool.ts` | 读取文本文件、图片、PDF、Jupyter notebooks，支持 offset/limit 分页 |
| `Edit` | `src/tools/FileEditTool/FileEditTool.ts` | 字符串替换式文件编辑，支持验证和 LSP 集成 |
| `Glob` | `src/tools/GlobTool/GlobTool.ts` | 文件模式匹配搜索 |
| `Grep` | `src/tools/GrepTool/GrepTool.ts` | 文件内容搜索（基于 ripgrep）|

#### 代码分析与导航
| 工具名 | 功能描述 |
|--------|----------|
| `LSP` | 语言服务器协议集成，代码导航和诊断 |
| `Tree` | 目录树结构展示 |

#### Agent 与子任务工具
| 工具名 | 功能描述 |
|--------|----------|
| `Agent` | 子 Agent 执行，支持并行任务 |
| `Task` | 后台任务管理 |

#### 外部集成工具
| 工具名 | 功能描述 |
|--------|----------|
| `Bash` | Bash 命令执行（受权限控制）|
| `WebFetch` | 网页内容获取 |
| `WebSearch` | 网络搜索 |
| `MCP` | Model Context Protocol 工具调用 |

#### 技能与命令工具
| 工具名 | 功能描述 |
|--------|----------|
| `Skill` | 调用 Slash Command 作为技能 |

#### 系统与调试工具
| 工具名 | 功能描述 |
|--------|----------|
| `REPL` | 交互式 REPL 环境（实验性功能）|
| `Sleep` | 延迟执行（实验性功能）|
| `Cron` | 定时任务调度（实验性功能）|
| `RemoteTrigger` | 远程触发器（实验性功能）|

### 1.4 工具执行流程

```
1. 用户输入 / 模型选择工具
       ↓
2. checkPermissions() - 权限检查
   - allow: 直接执行
   - deny: 拒绝执行
   - ask: 请求用户确认
       ↓
3. call() - 执行工具逻辑
       ↓
4. renderResult() - 渲染执行结果
       ↓
5. 结果返回给模型/用户
```

### 1.5 权限控制系统

权限检查返回三种结果：
- `allow`: 允许执行
- `deny`: 拒绝执行（可附带原因）
- `ask`: 需要用户确认

**权限规则配置：**
```typescript
// 示例：BashTool 的权限检查
async checkPermissions(params: string, context: ToolUseContext) {
  const parsed = parseBashParams(params)

  // 检查危险命令
  if (isDangerousCommand(parsed.command)) {
    return { type: 'ask', message: 'This command may be dangerous. Proceed?' }
  }

  // 检查只读模式
  if (context.readOnly) {
    return { type: 'deny', reason: 'Cannot execute commands in read-only mode' }
  }

  return { type: 'allow' }
}
```

### 1.6 工具实现示例

#### FileReadTool 关键特性
- 支持多种文件类型：文本、图片、PDF、Jupyter notebooks
- 分页读取：通过 `offset` 和 `limit` 参数控制
- 图片处理：自动调整大小和 token 预算管理
- 文件去重：通过 `readFileState` 缓存避免重复读取

#### FileEditTool 关键特性
- 字符串替换编辑（非行号编辑）
- 验证机制：文件存在性、字符串匹配、冲突检测
- LSP 集成：编辑后诊断检查
- Git 集成：自动 diff 跟踪

#### SkillTool 关键特性
- 调用 Slash Command 作为技能
- 支持两种执行上下文：
  - `inline`: 在当前对话中展开执行
  - `fork`: 在子 Agent 中独立执行
- 远程技能加载：支持从远程加载 canonical skills

---

## 二、命令系统（Command System）

### 2.1 命令注册机制

命令注册位于 `src/commands.ts`：

```typescript
export function COMMANDS(): Command[]  // 获取所有命令（带缓存）
export function getCommands(options: GetCommandsOptions): Promise<Command[]>
```

**命令来源：**
1. 内置命令（`src/commands/` 目录）
2. 技能命令（Skills 系统）
3. 插件命令（Plugin 系统）
4. MCP 命令（Model Context Protocol）
5. 工作流命令（Workflow 系统）

### 2.2 命令类型定义

核心类型位于 `src/types/command.ts`：

```typescript
export type Command = CommandBase &
  (PromptCommand | LocalCommand | LocalJSXCommand)

export interface CommandBase {
  name: string
  description: string
  aliases?: string[]

  // 可用性控制
  availability?: CommandAvailability[]  // 'claude-ai' | 'console'
  isEnabled?: () => boolean
  isHidden?: boolean

  // 执行控制
  immediate?: boolean        // 立即执行（不等待停止点）
  isSensitive?: boolean      // 参数是否脱敏
  disableModelInvocation?: boolean  // 禁止模型调用
  userInvocable?: boolean    // 用户是否可调用
}
```

### 2.3 命令类型详解

#### PromptCommand（提示命令）
```typescript
export type PromptCommand = {
  type: 'prompt'
  progressMessage: string
  contentLength: number
  argNames?: string[]
  allowedTools?: string[]      // 限制可用工具
  model?: string               // 指定模型
  source: SettingSource | 'builtin' | 'mcp' | 'plugin'

  // 执行上下文
  context?: 'inline' | 'fork'
  agent?: string               // fork 时的 Agent 类型
  effort?: EffortValue

  // 路径匹配（技能可见性）
  paths?: string[]

  getPromptForCommand(args: string, context: ToolUseContext): Promise<ContentBlockParam[]>
}
```

#### LocalCommand（本地命令）
```typescript
export type LocalCommand = {
  type: 'local'
  supportsNonInteractive: boolean
  load: () => Promise<{ call: LocalCommandCall }>
}
```

#### LocalJSXCommand（React UI 命令）
```typescript
export type LocalJSXCommand = {
  type: 'local-jsx'
  load: () => Promise<{ call: LocalJSXCommandCall }>
}
```

### 2.4 内置命令列表

| 命令 | 类型 | 功能描述 |
|------|------|----------|
| `/init` | Prompt | 项目初始化，创建 CLAUDE.md、skills、hooks |
| `/commit` | Prompt | Git 提交，带安全协议 |
| `/review` | Prompt | PR 代码审查（本地 + ultrareview）|
| `/pr` | Prompt | PR 创建和管理 |
| `/test` | Prompt | 测试运行和分析 |
| `/fix` | Prompt | 自动修复代码问题 |
| `/explain` | Prompt | 代码解释 |
| `/doc` | Prompt | 文档生成 |
| `/refactor` | Prompt | 代码重构 |
| `/login` | LocalJSX | OAuth 登录流程 |
| `/logout` | Local | 退出登录 |
| `/settings` | LocalJSX | 设置管理 |
| `/theme` | Local | 主题切换 |
| `/clear` | Local | 清空对话 |
| `/help` | Local | 帮助信息 |
| `/exit` | Local | 退出程序 |

### 2.5 命令执行流程

```
用户输入命令
     ↓
解析命令名称和参数
     ↓
查找命令定义
     ↓
检查可用性（availability, isEnabled）
     ↓
根据命令类型执行：
   - PromptCommand → 构建提示 → 发送给模型
   - LocalCommand → 加载模块 → 执行 call()
   - LocalJSXCommand → 加载模块 → 渲染 React 组件
     ↓
处理执行结果
     ↓
更新对话状态
```

### 2.6 安全命令集合

```typescript
// src/commands.ts
export const REMOTE_SAFE_COMMANDS = new Set([
  'commit',
  'pr',
  'review',
  // ... 远程模式允许的安全命令
])

export const BRIDGE_SAFE_COMMANDS = new Set([
  // IDE Bridge 模式允许的安全命令
])
```

---

## 三、工具与命令的交互

### 3.1 SkillTool 桥接

`SkillTool` 是工具系统和命令系统的桥梁：

```typescript
// 在工具系统中调用命令
export const SkillTool = buildTool({
  name: 'Skill',
  async call(params, context) {
    const command = findCommand(params.name)

    if (command.type === 'prompt') {
      // 执行 PromptCommand
      const blocks = await command.getPromptForCommand(args, context)
      return { type: 'tool_result', content: blocks }
    }

    // 执行 Local/LocalJSX Command
    const module = await command.load()
    return module.call(args, context)
  }
})
```

### 3.2 执行上下文

```typescript
export interface ToolUseContext {
  // 对话相关
  messages: Message[]
  setMessages: (updater: (prev: Message[]) => Message[]) => void

  // 工具控制
  allowTool: CanUseToolFn
  denyTool: (toolName: string) => void

  // 状态访问
  readOnly: boolean
  isRemote: boolean

  // 回调函数
  onDone?: LocalJSXCommandOnDone
  onChangeDynamicMcpConfig?: (config: Record<string, ScopedMcpServerConfig>) => void
}
```

---

## 四、扩展机制

### 4.1 MCP（Model Context Protocol）

```typescript
// 动态加载外部工具
export async function getMcpTools(config: McpConfig): Promise<Tool[]> {
  const client = await connectMcpServer(config)
  const tools = await client.listTools()

  return tools.map(mcpTool => ({
    name: mcpTool.name,
    async call(params) {
      return client.callTool(mcpTool.name, JSON.parse(params))
    }
  }))
}
```

### 4.2 插件系统

```typescript
// 插件命令加载
export async function loadPluginCommands(): Promise<Command[]> {
  const plugins = await discoverPlugins()

  return plugins.flatMap(plugin =>
    plugin.manifest.commands.map(cmd => ({
      ...cmd,
      source: 'plugin',
      pluginInfo: {
        pluginManifest: plugin.manifest,
        repository: plugin.repository
      }
    }))
  )
}
```

### 4.3 技能系统

技能系统支持从多个来源加载：
1. 内置技能（`src/skills/`）
2. 项目本地技能（`.claude/skills/`）
3. 远程技能（GitHub 等）

---

## 五、关键设计决策

### 5.1 权限分层

1. **工具级权限**：`checkPermissions()` 细粒度控制
2. **命令级权限**：`availability` 和 `isEnabled` 控制可见性
3. **系统级权限**：`readOnly`、`isRemote` 等全局状态

### 5.2 懒加载机制

```typescript
// Local/LocalJSX Command 使用懒加载
const LazyCommand: LocalCommand = {
  type: 'local',
  async load() {
    // 动态导入，减少启动时间
    const module = await import('./heavy-implementation.js')
    return { call: module.call }
  }
}
```

### 5.3 响应式 UI

LocalJSXCommand 支持 React/Ink 渲染：

```typescript
const InteractiveCommand: LocalJSXCommand = {
  type: 'local-jsx',
  async load() {
    return {
      call: async (onDone, context, args) => {
        return (
          <InteractiveForm
            onSubmit={(result) => onDone(result)}
          />
        )
      }
    }
  }
}
```

---

## 六、总结

### 架构亮点

1. **模块化设计**：工具、命令、技能分离，职责清晰
2. **扩展性强**：MCP、插件、技能多重扩展点
3. **权限完善**：多层权限控制，安全可靠
4. **类型安全**：完整的 TypeScript 类型定义
5. **性能优化**：懒加载、缓存、分页等机制

### 可借鉴实践

1. **工具注册表**：集中管理 + 动态筛选
2. **权限三态**：allow/deny/ask 灵活控制
3. **命令多态**：Prompt/Local/LocalJSX 适应不同场景
4. **懒加载模式**：减少启动开销
5. **上下文传递**：统一的 ToolUseContext 设计

---

*文档生成时间：2026-04-06*
*基于 free-code-main 项目代码分析*
