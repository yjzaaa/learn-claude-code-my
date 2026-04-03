# Proposal: Consolidate and Refactor Python Models

## Overview

将散落在项目各处的 Python 模型集中到 `core/models/` 目录，使用继承和组合设计模式重构，减少代码重复，提高可维护性。

## Current State

模型分散在多个目录：
- `core/models/` - 主要模型（domain.py, dto.py, config.py, events.py 等）
- `core/models/tool_models.py` - 工具相关模型
- `core/models/event_models.py` - 事件相关模型
- `core/models/response_models.py` - 响应模型
- `core/models/websocket_models.py` - WebSocket 模型

问题：
1. **重复定义** - 类似字段在多个模型中重复（如 `dialog_id`, `timestamp`）
2. **缺乏继承** - 没有基类统一公共字段和行为
3. **难以维护** - 新增模型需要修改多个文件
4. **类型不一致** - 部分使用 TypedDict，部分使用 Pydantic BaseModel

## Proposed Changes

### 1. 引入基类层次结构

```
BaseModel (Pydantic)
├── Entity (业务实体基类: id, created_at, updated_at)
├── Event (事件基类: type, dialog_id, timestamp)
├── Response (响应基类: success, message)
└── Config (配置基类)
```

### 2. 使用 Mixin 组合公共行为

- `TimestampMixin` - 创建/更新时间
- `DialogRefMixin` - 对话引用
- `MetadataMixin` - 元数据容器

### 3. 合并相关模型

将细分的模型文件合并为逻辑分组：
- `entities.py` - 业务实体（Dialog, Message, ToolCall）
- `events.py` - 所有事件类型
- `api.py` - API 请求/响应模型
- `config.py` - 所有配置类

### 4. 统一类型系统

- 全部使用 Pydantic BaseModel
- 移除 TypedDict（仅保留必要的向后兼容）

## Goals

1. **减少代码量 30%+** - 通过继承消除重复字段
2. **单一职责** - 每个模型只做一件事
3. **易于扩展** - 新增模型只需继承基类
4. **类型安全** - 全项目统一使用 Pydantic

## Success Criteria

- [ ] 所有模型集中在 `core/models/` 目录
- [ ] 引入 3-4 个基类覆盖 80% 模型
- [ ] 模型定义总行数减少 30%
- [ ] 所有测试通过
- [ ] 类型检查零错误

## Related Files

- `core/models/*.py` - 所有现有模型文件
- `core/models/__init__.py` - 导出整理
- `docs/ARCHITECTURE.md` - 架构文档更新
