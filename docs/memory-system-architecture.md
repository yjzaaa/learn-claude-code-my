# Claude Code 记忆系统架构文档

## 概述

Claude Code 的记忆系统是一个多层级、文件驱动的持久化机制，用于在会话之间保存和检索上下文信息。记忆系统的核心目标是让未来的对话能够了解用户是谁、他们希望如何协作、应该避免或重复哪些行为，以及工作背后的上下文。

## 核心架构

### 1. 记忆类型体系 (Memory Types)

记忆被约束为四种离散类型，每种类型都有特定的用途和范围：

| 类型 | 描述 | 范围 | 保存时机 |
|------|------|------|----------|
| **user** | 用户角色、目标、责任和知识 | 始终私有 | 了解用户角色、偏好、责任时 |
| **feedback** | 用户对如何开展工作给出的指导 | 默认私有，项目约定可为团队 | 用户纠正("不要那样")或确认("就是这样")时 |
| **project** | 正在进行的工作、目标、计划、缺陷或事件 | 私有或团队，倾向团队 | 了解谁在做什么、为什么、何时截止时 |
| **reference** | 外部系统中信息位置的指针 | 通常为团队 | 了解外部系统资源时 |

### 2. 存储层次结构

```
~/.claude/                          # 记忆基础目录
└── projects/
    └── <sanitized-project-root>/   # 项目特定目录
        ├── memory/                 # 自动记忆目录
        │   ├── MEMORY.md           # 记忆索引入口点
        │   ├── user_role.md        # 用户记忆文件
        │   ├── feedback_testing.md # 反馈记忆文件
        │   ├── project_deadline.md # 项目记忆文件
        │   └── reference_linear.md # 参考记忆文件
        └── team/                   # 团队记忆目录 (TEAMMEM 功能)
            └── MEMORY.md           # 团队记忆索引
```

### 3. 核心模块

#### 3.1 路径管理 (`src/memdir/`)

- **paths.ts**: 管理记忆目录路径解析
  - `isAutoMemoryEnabled()`: 检查自动记忆是否启用
  - `getAutoMemPath()`: 获取自动记忆目录路径
  - `getAutoMemEntrypoint()`: 获取 MEMORY.md 路径
  - `isAutoMemPath()`: 验证路径是否在记忆目录内

- **memoryTypes.ts**: 定义记忆类型和行为指南
  - 四种记忆类型的完整规范
  - 保存/使用指南
  -  frontmatter 格式示例

- **memdir.ts**: 记忆目录核心操作
  - `buildMemoryPrompt()`: 构建记忆提示
  - `loadMemoryPrompt()`: 加载记忆到系统提示
  - `truncateEntrypointContent()`: 截断索引内容

#### 3.2 团队记忆 (`src/services/teamMemorySync/`)

- **watcher.ts**: 团队记忆文件监控
- **teamMemPaths.ts**: 团队记忆路径管理
- **teamMemPrompts.ts**: 团队记忆提示构建
- **secretScanner.ts**: 敏感信息扫描

#### 3.3 记忆提取 (`src/services/extractMemories/`)

- **extractMemories.ts**: 后台代理自动提取记忆
  - 在对话结束时运行
  - 分析会话内容识别值得记忆的信息
  - 自动写入记忆文件

#### 3.4 会话记忆 (`src/services/SessionMemory/`)

- **sessionMemory.ts**: 会话级记忆管理
- **prompts.ts**: 会话记忆提示模板

#### 3.5 记忆压缩 (`src/services/compact/`)

- **compact.ts**: 主动压缩对话上下文
- **microCompact.ts**: 微压缩机制
- **autoCompact.ts**: 自动压缩触发
- **sessionMemoryCompact.ts**: 会话记忆压缩

## 工作流程

### 记忆保存流程

```
1. 识别记忆时机
   └─> 用户明确说"记住"某事
   └─> 对话结束时自动提取 (EXTRACT_MEMORIES)

2. 选择记忆类型
   └─> user / feedback / project / reference

3. 创建记忆文件
   └─> 使用 frontmatter 格式
   └─> 保存到 memory/ 目录

4. 更新索引
   └─> 在 MEMORY.md 中添加指针
   └─> 索引条目：<150字符的单行描述
```

### 记忆加载流程

```
1. 会话启动
   └─> loadMemoryPrompt() 被调用

2. 检查启用状态
   └─> isAutoMemoryEnabled()
   └─> 检查 CLAUDE_CODE_DISABLE_AUTO_MEMORY

3. 构建提示
   └─> buildMemoryLines() 创建行为指南
   └─> 读取 MEMORY.md 内容
   └─> 截断至 200行 / 25KB

4. 注入系统提示
   └─> 记忆内容作为用户上下文附加
```

## 配置选项

### 环境变量

| 变量 | 作用 |
|------|------|
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | 禁用自动记忆 (1/true=关闭, 0/false=开启) |
| `CLAUDE_CODE_SIMPLE` | 简化模式 (--bare)，禁用记忆 |
| `CLAUDE_CODE_REMOTE_MEMORY_DIR` | 远程记忆目录覆盖 |
| `CLAUDE_COWORK_MEMORY_PATH_OVERRIDE` | Cowork 记忆路径覆盖 |

### 设置选项 (settings.json)

```json
{
  "autoMemoryEnabled": true,
  "autoMemoryDirectory": "/path/to/custom/memory"
}
```

## 功能标志

记忆系统由多个功能标志控制：

| 标志 | 描述 |
|------|------|
| `EXTRACT_MEMORIES` | 对话结束时自动提取记忆 |
| `TEAMMEM` | 启用团队记忆同步 |
| `CACHED_MICROCOMPACT` | 查询流中缓存的微压缩状态 |
| `COMPACTION_REMINDERS` | 智能压缩提醒 |
| `KAIROS` | 助手模式，使用每日日志而非 MEMORY.md |

## 技能集成

### /remember 技能

位于 `src/skills/bundled/remember.ts`，提供记忆审查功能：

1. 收集所有记忆层 (CLAUDE.md, CLAUDE.local.md, auto-memory)
2. 分类每条自动记忆条目
3. 识别清理机会 (重复、过时、冲突)
4. 生成结构化的晋升报告

## 安全考虑

1. **路径验证**: `validateMemoryPath()` 防止危险路径
2. **敏感信息扫描**: `teamMemSecretGuard.ts` 扫描密钥
3. **写权限控制**: 自动记忆路径有特殊的文件系统权限
4. **项目设置排除**: 不读取项目级设置中的 `autoMemoryDirectory`

## 最佳实践

### 什么应该保存
- 用户的角色和专业知识
- 明确的工作方式偏好
- 项目决策的"为什么"
- 外部系统的指针

### 什么不应该保存
- 代码模式、架构 (可从代码推导)
- Git 历史、近期变更
- 调试解决方案 (应在代码/提交中)
- 已在 CLAUDE.md 中记录的内容
- 临时任务细节

### 记忆漂移处理
- 记忆可能随时间变得陈旧
- 在基于记忆推荐前验证文件/函数存在性
- 如果记忆与当前信息冲突，优先信任当前状态
- 更新或删除过时的记忆

## 相关文件

```
src/memdir/
├── memdir.ts              # 核心记忆目录操作
├── memoryTypes.ts         # 记忆类型定义
├── paths.ts               # 路径管理
├── teamMemPaths.ts        # 团队记忆路径
├── teamMemPrompts.ts      # 团队记忆提示
├── memoryAge.ts           # 记忆老化管理
├── memoryScan.ts          # 记忆扫描
└── findRelevantMemories.ts # 相关记忆查找

src/services/
├── extractMemories/       # 自动记忆提取
├── teamMemorySync/        # 团队记忆同步
├── SessionMemory/         # 会话记忆
└── compact/               # 记忆压缩

src/skills/bundled/
└── remember.ts            # 记忆审查技能
```
