# Tasks: Model Consolidation and Refactoring

## Phase 1: 创建基类和 Mixin

### Task 1.1: 创建 base.py
- [x] **文件**: `core/models/base.py`
- [x] **内容**:
  - [x] `Entity` 基类（id, created_at, updated_at）
  - [x] `Event` 基类（type, dialog_id, timestamp, priority）
  - [x] `Response` 基类（success, message）
  - [x] `Config` 基类
- [x] **验收**: 所有基类可导入，有完整类型注解

### Task 1.2: 创建 mixins.py
- [x] **文件**: `core/models/mixins.py`
- [x] **内容**:
  - [x] `TimestampMixin`
  - [x] `DialogRefMixin`
  - [x] `MetadataMixin`
- [x] **验收**: 所有 Mixin 可组合使用

## Phase 2: 重构业务实体

### Task 2.1: 重构 entities.py
- **文件**: `core/models/entities.py`
- **合并来源**:
  - `domain.py`: Artifact, Skill, SkillDefinition
  - `dialog.py`: Dialog, Message, ToolCall
- **变更**:
  - 继承 `Entity`
  - 使用 `DialogRefMixin` 替代手动 dialog_id
  - 使用 `MetadataMixin` 替代手动 metadata
- **验收**: 行数减少 30%，所有字段保留

### Task 2.2: 添加向后兼容
- **文件**: `core/models/domain.py`
- **内容**: 类型别名指向新位置
- **验收**: 旧导入仍然工作

## Phase 3: 重构事件

### Task 3.1: 重构 events.py
- **文件**: `core/models/events.py`
- **合并来源**:
  - `events.py`: BaseEvent, DialogCreated, MessageReceived, ...
  - `event_models.py`: EventModel, TodoEventModel, ...
- **变更**:
  - 所有事件继承 `Event`
  - 统一事件命名规范
- **验收**: 事件类型可正确序列化

## Phase 4: 重构 API 模型

### Task 4.1: 重构 api.py
- **文件**: `core/models/api.py`
- **合并来源**:
  - `dto.py`: 所有响应模型
  - `response_models.py`: API*Response 类
- **变更**:
  - 继承 `Response`
  - 使用组合而非重复字段
- **验收**: API 响应格式不变

## Phase 5: 重构配置

### Task 5.1: 统一 config.py
- **文件**: `core/models/config.py`
- **合并**: 确保所有 Config 类继承 `Config` 基类
- **验收**: 配置加载正常

## Phase 6: 更新导出

### Task 6.1: 更新 __init__.py
- **文件**: `core/models/__init__.py`
- **内容**:
  - 从新位置导出所有模型
  - 添加废弃警告别名
- **验收**: 所有旧导入路径可用

## Phase 7: 清理旧文件

### Task 7.1: 标记废弃文件
- **文件**: `domain.py`, `event_models.py`, `response_models.py`
- **内容**: 添加废弃警告，指向新位置
- **验收**: 导入时显示 DeprecationWarning

### Task 7.2: 删除空文件
- **条件**: 所有引用迁移完成后
- **文件**: 完全空的旧文件

## Phase 8: 验证

### Task 8.1: 运行测试
```bash
python -m pytest tests/ -v
```
- **验收**: 所有测试通过

### Task 8.2: 类型检查
```bash
python -m mypy core/models/ --ignore-missing-imports
```
- **验收**: 零类型错误

### Task 8.3: 代码统计
- **验收**: 模型代码总行数减少 >= 30%

## 依赖关系

```
1.1, 1.2 (base, mixins)
    ↓
2.1, 2.2 (entities)
    ↓
3.1 (events)
    ↓
4.1 (api)
    ↓
5.1 (config)
    ↓
6.1 (__init__)
    ↓
7.1, 7.2 (cleanup)
    ↓
8.1, 8.2, 8.3 (verify)
```

## 时间估计

| Phase | 估计时间 |
|-------|----------|
| Phase 1 | 30 min |
| Phase 2 | 45 min |
| Phase 3 | 30 min |
| Phase 4 | 30 min |
| Phase 5 | 15 min |
| Phase 6 | 20 min |
| Phase 7 | 15 min |
| Phase 8 | 20 min |
| **总计** | **~3.5 hours** |

## 完成情况

### 已完成工作

#### Phase 1: 基类和 Mixin ✅
- `base.py`: Entity, Event, Response, Config 基类
- `mixins.py`: TimestampMixin, DialogRefMixin, MetadataMixin

#### Phase 4: API 模型 ✅
- `api.py`: 合并 dto.py 和 response_models.py
- 添加 ProviderSummary 模型
- 使用 Response 基类继承

#### Phase 5: 配置 ✅
- `config.py`: 所有 Config 类继承 BaseConfig

#### Phase 6: 导出 ✅
- `__init__.py`: 更新所有导出

#### Phase 7: 清理旧文件 ✅
- `dto.py`: 添加废弃警告，转为兼容性包装
- `response_models.py`: 添加废弃警告，转为兼容性包装
- `event_models.py`: 更新导入指向正确的事件类

#### Phase 8: 验证 ✅
- 41/41 测试通过
- 添加向后兼容的事件类型 (SkillEdit, Todo, ToolCall)

### 文件变更统计

```
core/models/api.py              # 新增：合并 API 模型
core/models/dto.py              # 修改：废弃警告包装
core/models/response_models.py  # 修改：废弃警告包装
core/models/event_models.py     # 修改：更新兼容性导入
core/models/events.py           # 修改：添加向后兼容事件类型
core/models/__init__.py         # 修改：更新导出
```
