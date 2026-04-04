# Claude Code 记忆系统文档

本目录包含 Claude Code 记忆系统的完整架构文档。

## 文档列表

| 文档 | 描述 |
|------|------|
| [memory-system-architecture.md](./memory-system-architecture.md) | 记忆系统整体架构、核心模块、配置选项 |
| [memory-file-format.md](./memory-file-format.md) | 记忆文件格式规范、frontmatter 示例 |
| [memory-workflows.md](./memory-workflows.md) | 记忆系统各工作流程详解 |
| [memory-system-comparison.md](./memory-system-comparison.md) | Claude Code vs Deep Agent 记忆系统对比 |
| [context-compact-comparison.md](./context-compact-comparison.md) | 上下文压缩机制深度对比 |

## 快速概览

### 什么是记忆系统？

Claude Code 的记忆系统是一个**文件驱动的持久化机制**，用于在会话之间保存上下文信息。它让 Claude 能够：

- 了解用户的角色和偏好
- 记住用户的反馈和指导
- 跟踪项目上下文和决策
- 记录外部系统指针

### 四种记忆类型

1. **user** - 用户角色、目标、知识
2. **feedback** - 工作方式指导
3. **project** - 项目上下文
4. **reference** - 外部系统指针

### 存储位置

```
~/.claude/projects/
└── <project-slug>/
    └── memory/
        ├── MEMORY.md      # 索引文件
        └── *.md           # 记忆文件
```

### 核心功能

- **自动提取** - 对话结束时自动识别并保存记忆
- **团队同步** - 多用户间共享团队记忆
- **记忆压缩** - 长对话自动压缩保留关键信息
- **记忆审查** - /remember 技能帮助整理和晋升记忆

## 关键代码路径

```
src/memdir/              # 核心记忆目录
src/services/
  ├── extractMemories/   # 自动记忆提取
  ├── teamMemorySync/    # 团队记忆同步
  ├── SessionMemory/     # 会话记忆
  └── compact/           # 记忆压缩
src/skills/bundled/
  └── remember.ts        # 记忆审查技能
```

## 功能标志

- `EXTRACT_MEMORIES` - 自动记忆提取
- `TEAMMEM` - 团队记忆
- `CACHED_MICROCOMPACT` - 微压缩缓存
- `KAIROS` - 助手模式（每日日志）

## 相关资源

- 主项目：[Claude Code](https://github.com/anthropics/claude-code)
- 记忆提示工程：`src/memdir/memoryTypes.ts`
