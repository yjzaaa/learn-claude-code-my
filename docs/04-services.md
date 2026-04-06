# free-code 服务层和基础设施分析

## 1. 概述

free-code 的服务层和基础设施提供了核心功能支持，包括 API 客户端、OAuth 认证、MCP 集成、IDE 桥接和任务管理等。这些服务构成了应用与外部系统交互的桥梁。

## 2. API 客户端 (src/services/api/)

### 2.1 核心文件

| 文件 | 功能 |
|------|------|
| `client.ts` | Anthropic SDK 客户端创建和配置 |
| `claude.ts` | Claude API 调用封装 |
| `codex-fetch-adapter.ts` | OpenAI Codex API 适配器 |
| `errors.ts` | API 错误定义和处理 |
| `withRetry.ts` | 请求重试逻辑 |

### 2.2 多提供商支持

支持的 LLM 提供商:
- Anthropic (默认): ANTHROPIC_API_KEY
- OpenAI Codex: CLAUDE_CODE_USE_OPENAI=1
- AWS Bedrock: CLAUDE_CODE_USE_BEDROCK=1
- Google Vertex AI: CLAUDE_CODE_USE_VERTEX=1
- Anthropic Foundry: CLAUDE_CODE_USE_FOUNDRY=1

### 2.3 Claude API 集成

**文件**: `src/services/api/claude.ts`

主要功能：
- 流式消息处理
- 工具调用执行
- 上下文压缩管理
- 使用统计追踪

### 2.4 Codex 适配器

**文件**: `src/services/api/codex-fetch-adapter.ts`

将 Anthropic Messages API 格式转换为 OpenAI Responses API 格式。

**支持的模型**：
- `gpt-5.2-codex` - Frontier agentic coding model
- `gpt-5.1-codex` - Codex coding model
- `gpt-5.1-codex-mini` - Fast Codex model
- `gpt-5.1-codex-max` - Max Codex model

**协议转换**：
- Anthropic `tool_use` to OpenAI `function_call`
- Anthropic `tool_result` to OpenAI `function_call_output`
- 系统提示词 to instructions
- 流式 SSE 事件翻译

## 3. OAuth 认证 (src/services/oauth/)

### 3.1 架构概览

```
OAuthService -> AuthCodeListener -> Local Server
                    |
                    v
              Token Store
```

### 3.2 核心组件

| 文件 | 功能 |
|------|------|
| `index.ts` | OAuthService 主类，处理完整 OAuth 流程 |
| `client.ts` | Anthropic OAuth 客户端实现 |
| `codex-client.ts` | OpenAI Codex OAuth 客户端 |
| `auth-code-listener.ts` | 本地回调服务器 |
| `crypto.ts` | PKCE 加密工具 |

### 3.3 Anthropic OAuth Token 结构

```typescript
interface OAuthTokens {
  accessToken: string
  refreshToken: string
  expiresAt: number
  scopes: string[]
  subscriptionType: 'max' | 'pro' | 'enterprise' | 'team' | null
  rateLimitTier: string | null
}
```

### 3.4 OpenAI Codex OAuth

**独立实现**：`codex-client.ts`

- 固定端口 1455（OpenAI 注册的重定向 URI）
- PKCE 流程
- JWT 账户 ID 提取
- Token 刷新机制

## 4. MCP 集成 (src/services/mcp/)

### 4.1 架构概述

MCP (Model Context Protocol) 允许连接外部工具服务器。

支持的服务器类型:
- STDIO Servers
- SSE Servers
- HTTP/WS Servers
- Claude.ai Proxy Servers

### 4.2 核心文件

| 文件 | 功能 |
|------|------|
| `client.ts` | MCP 客户端管理器（3000+ 行） |
| `config.ts` | 配置解析和验证 |
| `types.ts` | TypeScript 类型定义 |
| `claudeai.ts` | Claude.ai 代理服务器支持 |
| `auth.ts` | MCP OAuth 认证处理 |

### 4.3 服务器配置类型

```typescript
type Transport = 'stdio' | 'sse' | 'sse-ide' | 'http' | 'ws' | 'sdk'

interface McpStdioServerConfig {
  type?: 'stdio'
  command: string
  args: string[]
  env?: Record<string, string>
}

interface McpSSEServerConfig {
  type: 'sse'
  url: string
  headers?: Record<string, string>
  oauth?: McpOAuthConfig
}
```

### 4.4 连接状态管理

```typescript
type MCPServerConnection =
  | ConnectedMCPServer
  | FailedMCPServer
  | NeedsAuthMCPServer
  | PendingMCPServer
  | DisabledMCPServer
```

### 4.5 Claude.ai 代理服务器

**文件**: `src/services/mcp/claudeai.ts`

从 Claude.ai 组织配置获取 MCP 服务器：
- 检查 OAuth token 和 user:mcp_servers scope
- 调用 /v1/mcp_servers API
- 返回服务器配置映射

## 5. 桥接系统 (src/bridge/)

### 5.1 架构概述

桥接系统支持与 IDE 的集成和远程控制功能。

组件:
- IDE Bridge (VS Code/JetBrains)
- Remote Control (CCR - Claude Code Remote)

### 5.2 IDE 桥接

**核心文件**：
- `bridgeMain.ts` - IDE 桥接主逻辑
- `bridgeApi.ts` - API 客户端
- `bridgeMessaging.ts` - 消息处理

**功能**：
- VS Code 扩展集成
- JetBrains 插件集成
- 双向消息传递
- 文件变更通知

### 5.3 远程控制 (CCR)

**文件**: `src/bridge/remoteBridgeCore.ts`

Env-less Remote Control 桥接核心流程：
1. POST /v1/code/sessions - 创建会话
2. POST /v1/code/sessions/{id}/bridge - 获取 worker JWT
3. createV2ReplTransport - 建立 SSE + CCRClient 传输
4. Token 刷新调度
5. 401 恢复机制

### 5.4 桥接类型定义

**文件**: `src/bridge/types.ts`

```typescript
interface BridgeConfig {
  dir: string
  machineName: string
  branch: string
  gitRepoUrl: string | null
  maxSessions: number
  spawnMode: 'single-session' | 'worktree' | 'same-dir'
  workerType: 'claude_code' | 'claude_code_assistant'
}

interface SessionHandle {
  sessionId: string
  done: Promise<SessionDoneStatus>
  kill(): void
  forceKill(): void
  activities: SessionActivity[]
  accessToken: string
}
```

## 6. 任务管理 (src/Task.ts)

### 6.1 任务类型

```typescript
type TaskType =
  | 'local_bash'      // 本地 bash 命令
  | 'local_agent'     // 本地 Agent
  | 'remote_agent'    // 远程 Agent
  | 'in_process_teammate' // 进程内队友
  | 'local_workflow'  // 本地工作流
  | 'monitor_mcp'     // MCP 监控
  | 'dream'           // Dream 任务
```

### 6.2 任务状态

```typescript
type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'killed'

function isTerminalTaskStatus(status: TaskStatus): boolean {
  return status === 'completed' || status === 'failed' || status === 'killed'
}
```

### 6.3 任务 ID 生成

```typescript
const TASK_ID_PREFIXES: Record<string, string> = {
  local_bash: 'b',
  local_agent: 'a',
  remote_agent: 'r',
  in_process_teammate: 't',
  local_workflow: 'w',
  monitor_mcp: 'm',
  dream: 'd',
}

// 36^8 ≈ 2.8 trillion 组合
export function generateTaskId(type: TaskType): string
```

## 7. 其他服务

### 7.1 分析服务

| 服务 | 文件 | 功能 |
|------|------|------|
| Analytics | `src/services/analytics/` | 事件追踪和遥测 |
| Session Memory | `src/services/SessionMemory/` | 会话记忆管理 |
| Magic Docs | `src/services/MagicDocs/` | 智能文档生成 |
| Compact | `src/services/compact/` | 上下文压缩 |

### 7.2 工具服务

| 服务 | 文件 | 功能 |
|------|------|------|
| LSP Client | `src/services/lsp/` | 语言服务器协议客户端 |
| Voice | `src/services/voice*.ts` | 语音输入处理 |
| Auto Dream | `src/services/autoDream/` | 自动梦境总结 |

## 8. 外部 API 集成

### 8.1 Anthropic API

- **端点**: `https://api.anthropic.com/v1/messages`
- **认证**: API Key 或 OAuth
- **功能**: 流式聊天、工具调用、上下文管理

### 8.2 OpenAI Codex API

- **端点**: `https://chatgpt.com/backend-api/codex/responses`
- **认证**: OAuth (JWT)
- **功能**: 代码生成、工具执行

### 8.3 Claude.ai API

- **端点**: `https://claude.ai/api`
- **认证**: OAuth
- **功能**: 用户配置、MCP 服务器、远程控制

## 9. 依赖关系

```
services/
├── api/
│   ├── client.ts <- @anthropic-ai/sdk
│   ├── claude.ts <- client.ts
│   └── codex-fetch-adapter.ts <- OpenAI API
├── oauth/
│   ├── index.ts <- client.ts, codex-client.ts
│   ├── client.ts <- axios
│   └── codex-client.ts <- http
├── mcp/
│   ├── client.ts <- @modelcontextprotocol/sdk
│   ├── claudeai.ts <- axios
│   └── config.ts <- zod
└── bridge/
    ├── remoteBridgeCore.ts <- axios
    └── replBridge.ts <- ws
```

## 10. 总结

free-code 的服务层设计具有以下特点：

1. **多提供商支持**: 通过适配器模式支持多种 LLM 提供商
2. **灵活的 MCP 集成**: 支持多种传输协议的 MCP 服务器
3. **完整的 OAuth 实现**: 支持 Anthropic 和 OpenAI 的 OAuth 流程
4. **强大的桥接能力**: 支持 IDE 集成和远程控制
5. **健壮的任务管理**: 支持多种任务类型和状态管理
