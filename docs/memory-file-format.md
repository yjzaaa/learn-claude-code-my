# 记忆文件格式规范

## 文件结构

记忆系统使用 Markdown 文件存储记忆，每个记忆一个文件。

## Frontmatter 格式

每个记忆文件必须包含 YAML frontmatter：

```markdown
---
name: {{记忆名称}}
description: {{单行描述 - 用于判断相关性，需具体}}
type: {{user, feedback, project, reference}}
---

{{记忆内容 - feedback/project 类型需包含：**Why:** 和 **How to apply:**}}
```

## 类型详解

### User 类型

用于记录用户的角色、目标和知识。

```markdown
---
name: User role - Data scientist
description: User is a data scientist focused on observability
type: user
---

User is a data scientist currently investigating logging infrastructure.
Previously worked on ML pipelines before transitioning to observability.
```

### Feedback 类型

用于记录用户对如何开展工作的指导。

```markdown
---
name: Database testing policy
description: Integration tests must use real database, not mocks
type: feedback
---

Integration tests must hit a real database, not mocks.

**Why:** Prior incident where mock/prod divergence masked a broken migration.

**How to apply:** Always set up test database containers for integration tests.
Never use mocked database responses in tests that verify SQL correctness.
```

### Project 类型

用于记录项目上下文，非代码可推导的信息。

```markdown
---
name: Auth middleware rewrite
description: Auth rewrite driven by compliance requirements
type: project
---

Auth middleware rewrite is driven by legal/compliance requirements around
session token storage, not tech-debt cleanup.

**Why:** Legal flagged current storage for new compliance requirements.

**How to apply:** Favor compliance over ergonomics in scope decisions.
Timeline: Must complete by 2026-04-15 for audit.
```

### Reference 类型

用于记录外部系统指针。

```markdown
---
name: Pipeline bug tracker
description: Pipeline bugs tracked in Linear project INGEST
type: reference
---

Pipeline bugs are tracked in Linear project "INGEST".
Check https://linear.app/company/project/INGEST for context on pipeline tickets.
```

## MEMORY.md 索引格式

MEMORY.md 是记忆的入口点，作为索引而非记忆存储：

```markdown
- [User role](user_role.md) — Data scientist focused on observability
- [Testing policy](feedback_testing.md) — Use real database in integration tests
- [Auth rewrite](project_auth.md) — Compliance-driven middleware rewrite
- [Bug tracker](reference_linear.md) — Linear project INGEST for pipeline bugs
```

**规则：**
- 每个条目一行
- 长度控制在 ~150 字符以内
- 使用 `- [标题](文件.md) — 描述` 格式
- 不直接写记忆内容
- 按主题组织，非按时间

## 文件命名约定

- 使用小写
- 单词间用连字符或下划线
- 包含类型前缀（可选但推荐）：
  - `user_*.md`
  - `feedback_*.md`
  - `project_*.md`
  - `reference_*.md`

## 存储位置

```
~/.claude/projects/
└── <project-slug>/
    └── memory/
        ├── MEMORY.md           # 索引文件
        ├── user_role.md        # 用户记忆
        ├── feedback_*.md       # 反馈记忆
        ├── project_*.md        # 项目记忆
        └── reference_*.md      # 参考记忆
```

## 更新与维护

### 创建新记忆

1. 创建新的 `.md` 文件
2. 填写 frontmatter
3. 编写内容
4. 在 MEMORY.md 中添加索引条目

### 更新现有记忆

1. 修改 `.md` 文件内容
2. 同步更新 frontmatter 中的描述
3. 如有必要，更新 MEMORY.md 中的索引描述

### 删除记忆

1. 删除 `.md` 文件
2. 从 MEMORY.md 中移除对应条目

## 内容指南

### 应该包含

- 具体的、可操作的指导
- 明确的"为什么"和"如何应用"
- 绝对日期（如 2026-04-04）而非相对日期
- 外部资源的完整 URL

### 不应该包含

- 代码片段（应在代码库中）
- Git 历史信息
- 临时性任务状态
- 可从代码直接推导的信息
