# free-code 记忆系统深度分析

## 1. 概述

free-code 的记忆系统是一个多层次、多模式的持久化机制，用于在会话之间保留和回忆上下文信息。系统设计精巧，支持个人记忆和团队记忆，并包含自动提取、老化管理和相关性检索等高级功能。

### 1.1 核心特性

| 特性 | 说明 |
|------|------|
| **四级记忆类型** | user, feedback, project, reference |
| **双模式存储** | 个人记忆 + 团队记忆 |
| **自动提取** | 后台 Agent 自动从对话中提取记忆 |
| **会话记忆** | 当前会话的实时笔记 |
| **相关性检索** | 基于查询智能选择相关记忆 |
| **老化管理** | 记忆新鲜度追踪和过期提示 |

---

## 2. 记忆类型系统

### 2.1 四种记忆类型

**定义文件**: `src/memdir/memoryTypes.ts`

```typescript
export const MEMORY_TYPES = [
  'user',      // 用户信息
  'feedback',  // 反馈指导
  'project',   // 项目信息
  'reference', // 外部引用
] as const
```

### 2.2 类型详解

#### **user - 用户记忆**
- **范围**: 始终私有
- **内容**: 用户角色、目标、责任、知识背景
- **保存时机**: 了解用户任何细节时
- **使用方式**: 根据用户画像调整回应风格

**示例**:
```markdown
---
type: user
description: 用户是数据科学家，专注于可观测性/日志
---

用户正在调查现有的日志记录机制。
```

#### **feedback - 反馈记忆**
- **范围**: 默认私有，项目级约定可存团队
- **内容**: 用户指导（避免/保持的做法）
- **保存时机**: 用户纠正或确认时
- **结构**: 规则 + Why + How to apply

**示例**:
```markdown
---
type: feedback
---

**规则**: 集成测试必须连接真实数据库，不使用 mock
**Why**: 上季度 mock 测试通过但生产迁移失败
**How to apply**: 所有数据库相关测试
```

#### **project - 项目记忆**
- **范围**: 私有或团队（偏向团队）
- **内容**: 进行中的工作、目标、截止日期、事件
- **保存时机**: 了解项目动态时
- **结构**: 事实 + Why + How to apply

**示例**:
```markdown
---
type: project
description: 合并冻结开始日期
---

**事实**: 2026-03-05 开始合并冻结
**Why**: 移动团队要切 release 分支
**How to apply**: 标记该日期后的非关键 PR 工作
```

#### **reference - 引用记忆**
- **范围**: 通常是团队
- **内容**: 外部系统信息位置
- **保存时机**: 了解外部资源时
- **用途**: 快速查找外部信息

**示例**:
```markdown
---
type: reference
description: Linear 项目追踪
---

管道 bug 在 Linear 项目 "INGEST" 中追踪
```

### 2.3 不应保存的内容

根据代码注释，以下内容**不应**作为记忆：
- 代码模式（可通过 grep/git 推导）
- 架构信息（可在 CLAUDE.md 中找到）
- Git 历史
- 文件结构

---

## 3. 存储架构

### 3.1 目录结构

```
~/.claude/                          # 配置根目录
└── projects/                       # 项目记忆
    └── <sanitized-project-path>/   # 项目目录
        └── memory/                 # 记忆目录
            ├── MEMORY.md           # 入口文件（索引）
            ├── user/               # 用户记忆
            ├── feedback/           # 反馈记忆
            ├── project/            # 项目记忆
            ├── reference/          # 引用记忆
            └── logs/               # 每日日志（可选）
                └── YYYY/MM/YYYY-MM-DD.md
```

### 3.2 团队记忆

**条件**: `TEAMMEM` 功能标志启用

```
memory/                      # 个人记忆
├── MEMORY.md
├── user/
├── feedback/
├── project/
└── reference/

team-memory/                 # 团队记忆（TEAMMEM）
├── MEMORY.md
├── feedback/               # 团队级反馈
├── project/                # 团队级项目信息
└── reference/              # 团队级引用
```

### 3.3 路径解析

**文件**: `src/memdir/paths.ts`

**优先级**（从高到低）:
1. `CLAUDE_COWORK_MEMORY_PATH_OVERRIDE` - SDK 覆盖
2. `autoMemoryDirectory` in settings.json - 用户设置
3. `<memoryBase>/projects/<sanitized-path>/memory/` - 默认

**安全检查**:
- 拒绝相对路径（`../foo`）
- 拒绝根目录（`/`）
- 拒绝 UNC 路径（`\\server\share`）
- 拒绝 null 字节
- 拒绝 URL 编码遍历（`%2e%2e%2f`）

---

## 4. 自动记忆提取

### 4.1 提取机制

**文件**: `src/services/extractMemories/extractMemories.ts`

**触发时机**:
- 每次完整查询循环结束时（模型产生最终响应且无工具调用）
- 通过 `handleStopHooks` 在 `stopHooks.ts` 中调用

**执行模式**:
- 使用 **forked agent** 模式
- 共享父对话的 prompt cache
- 不中断主对话流程

### 4.2 提取流程

```
查询结束
    ↓
检查条件（消息数、功能开关）
    ↓
扫描现有记忆文件
    ↓
构建提取 Prompt
    ↓
运行 Forked Agent
    ↓
保存提取的记忆
    ↓
更新游标位置
```

### 4.3 互斥机制

主 Agent 和后台提取 Agent **互斥**:
- 如果主 Agent 已写入记忆 → 后台跳过
- 检测方法: `hasMemoryWritesSince(cursorUuid)`
- 避免重复写入相同的观察

### 4.4 会话记忆（Session Memory）

**文件**: `src/services/SessionMemory/sessionMemory.ts`

**功能**:
- 自动维护当前会话的 markdown 笔记
- 后台 forked subagent 定期提取
- 不中断主对话

**触发条件**:
- 初始化阈值：首次满足条件时创建
- 更新阈值：每 N 条消息或 M 个工具调用

---

## 5. 记忆检索

### 5.1 相关性检索

**文件**: `src/memdir/findRelevantMemories.ts`

**流程**:
```
用户查询
    ↓
扫描记忆目录（最多200个文件）
    ↓
读取 frontmatter（前30行）
    ↓
构建记忆清单
    ↓
调用 Sonnet 选择最相关的（最多5个）
    ↓
返回文件路径列表
```

### 5.2 选择算法

**系统提示词**:
```
You are selecting memories that will be useful to Claude Code...
Return a list of filenames for the memories that will clearly be useful...
- If unsure, do not include
- If no memories are useful, return empty list
- Exclude recently used tool docs
```

### 5.3 扫描实现

**文件**: `src/memdir/memoryScan.ts`

**优化**:
- 单次遍历：读取 + stat 合并
- 限制最多 200 个文件
- 只读取 frontmatter（前30行）
- 按修改时间排序（最新的在前）

### 5.4 文件格式

**Frontmatter**:
```markdown
---
type: user | feedback | project | reference
description: 简短描述（用于检索）
---

记忆内容...
```

---

## 6. 记忆老化管理

### 6.1 老化计算

**文件**: `src/memdir/memoryAge.ts`

```typescript
// 天数计算（向下取整）
export function memoryAgeDays(mtimeMs: number): number {
  return Math.max(0, Math.floor((Date.now() - mtimeMs) / 86_400_000))
}

// 人性化显示
export function memoryAge(mtimeMs: number): string {
  const d = memoryAgeDays(mtimeMs)
  if (d === 0) return 'today'
  if (d === 1) return 'yesterday'
  return `${d} days ago`
}
```

### 6.2 新鲜度提示

**超过1天的记忆会附加警告**:
```
This memory is 47 days old.
Memories are point-in-time observations, not live state —
claims about code behavior or file:line citations may be outdated.
Verify against current code before asserting as fact.
```

### 6.3 老化策略

- **≤ 1 天**: 无提示（today/yesterday）
- **> 1 天**: 附加 `<system-reminder>` 警告
- 模型根据警告自行判断记忆的可靠性

---

## 7. 入口文件 (MEMORY.md)

### 7.1 作用

MEMORY.md 是记忆目录的索引文件：
- 列出现有记忆文件
- 提供记忆类型指导
- 作为系统提示词的一部分注入

### 7.2 大小限制

```typescript
const MAX_ENTRYPOINT_LINES = 200      // 最多200行
const MAX_ENTRYPOINT_BYTES = 25_000   // 最多25KB
```

**超出限制时**: 截断并附加警告

### 7.3 内容结构

```markdown
# Memory

## Types of memory

（四种记忆类型的详细说明和示例）

## Memory files

- [user/profile.md](user/profile.md) - 用户角色和偏好
- [project/deadlines.md](project/deadlines.md) - 项目截止日期
- ...
```

---

## 8. 记忆 Prompt 构建

### 8.1 系统提示词注入

**文件**: `src/memdir/memdir.ts`

**功能**: `loadMemoryPrompt()`

**注入内容**:
1. MEMORY.md 入口文件（截断后）
2. 记忆类型指导（4种类型详解）
3. 何时访问记忆
4. 不保存的内容
5. 信任回忆建议

### 8.2 提示词结构

```
<memory>
## Memory
（MEMORY.md 内容）

## Types of memory
（四种类型详解）

## When to access memories
（访问时机）

## What NOT to save in memory
（排除内容）

## Trusting your recall
（回忆建议）
</memory>
```

---

## 9. 记忆与压缩

### 9.1 上下文压缩

当对话超过上下文窗口时：
- 旧消息被压缩/移除
- **记忆持久化**: 已写入 MEMORY.md 的信息不会丢失
- 会话记忆: 可重新初始化

### 9.2 记忆 vs 会话存储

| 特性 | 记忆系统 | 会话存储 |
|------|----------|----------|
| 持久化 | 是（磁盘文件） | 否（内存） |
| 跨会话 | 是 | 否 |
| 自动提取 | 是 | 是（SessionMemory）|
| 检索方式 | 相关性选择 | 完整加载 |

---

## 10. 安全与权限

### 10.1 路径安全

**验证**:
- 绝对路径检查
- 路径遍历防护（`../`）
- Unicode 规范化攻击防护
- URL 编码遍历防护

### 10.2 写入权限

**自动记忆路径特权**:
- 绕过 `DANGEROUS_DIRECTORIES` 限制
- 允许直接写入无需确认
- 仅限 `~/.claude/projects/` 下的路径

### 10.3 团队记忆安全

- `projectSettings` 被排除（防止恶意仓库配置）
- 仅接受 `policy/local/user` settings

---

## 11. 配置与开关

### 11.1 环境变量

| 变量 | 功能 |
|------|------|
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | 禁用自动记忆 |
| `CLAUDE_CODE_SIMPLE` | 简化模式（禁用记忆）|
| `CLAUDE_COWORK_MEMORY_PATH_OVERRIDE` | 记忆路径覆盖 |
| `CLAUDE_CODE_REMOTE_MEMORY_DIR` | 远程模式记忆目录 |

### 11.2 功能标志

| 标志 | 功能 |
|------|------|
| `EXTRACT_MEMORIES` | 启用后台记忆提取 |
| `TEAMMEM` | 启用团队记忆 |
| `MEMORY_SHAPE_TELEMETRY` | 记忆形状遥测 |

### 11.3 Settings.json

```json
{
  "autoMemoryEnabled": true,
  "autoMemoryDirectory": "~/custom/memory/path"
}
```

---

## 12. 代码文件索引

### 12.1 核心文件

| 文件 | 功能 | 行数 |
|------|------|------|
| `src/memdir/memoryTypes.ts` | 记忆类型定义 | 22,866 |
| `src/memdir/memdir.ts` | 主逻辑 | 21,174 |
| `src/memdir/paths.ts` | 路径管理 | 10,668 |
| `src/memdir/memoryScan.ts` | 文件扫描 | 3,105 |
| `src/memdir/findRelevantMemories.ts` | 相关性检索 | 5,305 |
| `src/memdir/memoryAge.ts` | 老化管理 | 1,931 |

### 12.2 服务层

| 文件 | 功能 |
|------|------|
| `src/services/extractMemories/extractMemories.ts` | 自动提取 |
| `src/services/extractMemories/prompts.ts` | 提取提示词 |
| `src/services/SessionMemory/sessionMemory.ts` | 会话记忆 |
| `src/services/SessionMemory/prompts.ts` | 会话记忆提示词 |

### 12.3 工具命令

| 文件 | 功能 |
|------|------|
| `src/commands/memory/memory.tsx` | `/memory` 命令 |

---

## 13. 总结

free-code 的记忆系统是一个设计精巧的多层次架构：

1. **类型系统**: 四种记忆类型覆盖不同场景
2. **存储架构**: 个人+团队双模式，安全的路径管理
3. **自动提取**: 后台 Agent 自动提取，不中断主对话
4. **智能检索**: 基于查询动态选择最相关的记忆
5. **老化管理**: 新鲜度提示，避免陈旧信息误导
6. **安全优先**: 多层路径验证，防止遍历攻击

这个系统实现了**持久化上下文**的目标，让 AI 助手能够在多次会话中保持对用户、项目和反馈的理解，同时避免信息过载通过相关性检索和老化管理来平衡。

---

*分析日期: 2026-04-06*
*分析文件: free-code src/memdir/ 及相关服务*
