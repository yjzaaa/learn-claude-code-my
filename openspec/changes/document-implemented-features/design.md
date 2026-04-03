## 设计：项目文档体系

## 背景

本项目是一个"nano Claude Code-like agent"学习项目，包含：
- 12个渐进式会话（s01-s12）教授Agent运行时核心机制
- 全栈参考实现（FastAPI后端 + Next.js前端）
- 六大管理器架构：Dialog、Tool、State、Provider、Memory、Skill

现有代码已实现完整功能，但缺乏系统化的项目文档。

## 目标

**目标：**
- 创建完整的项目文档体系，覆盖需求、架构、技术栈、API、数据库
- 确保新开发者能通过文档快速理解项目
- 建立可维护的知识资产

**非目标：**
- 不修改任何现有代码
- 不添加新功能
- 不改变项目架构

## 技术决策

### 1. 文档位置：根目录 `docs/` vs `openspec/specs/`

**决策：** 项目文档放在根目录 `docs/`，OpenSpec规格保留在 `openspec/specs/`

**理由：**
- `docs/` 是开发者第一眼看到的位置，符合惯例
- `openspec/specs/` 专注于变更驱动的规格定义
- 分离关注点：项目知识 vs 变更规格

### 2. 文档格式：Markdown

**决策：** 使用 Markdown 格式

**理由：**
- 与代码库版本控制集成
- 支持 GitHub/GitLab 渲染
- 轻量且广泛支持

### 3. 文档结构

```
docs/
├── README.md              # 文档导航和快速开始
├── requirements.md        # 功能需求（覆盖已实现功能）
├── architecture.md        # 分层架构和组件设计
├── tech_stack.md          # 技术选型和依赖
├── api_spec.md            # REST API + WebSocket
└── database_schema.md     # 数据模型和关系
```

## 风险与权衡

| 风险 | 缓解措施 |
|------|---------|
| 文档与代码不同步 | 在 CLAUDE.md 中添加代码大小限制提示 |
| 文档过于冗长 | 保持简洁，参考现有 CLAUDE.md 风格 |
| 重复信息 | 每个文档有明确单一职责 |

## 迁移计划

1. 创建所有文档文件
2. 更新 CLAUDE.md（如需要）
3. 验证文档链接和格式
4. 归档变更

## 开放问题

无
