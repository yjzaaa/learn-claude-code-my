## Why

后端代码中存在大量裸 JSON/dict 格式的数据，这些没有类型约束的数据容易导致运行时错误、API 契约破坏和维护困难。通过使用 Pydantic 模型进行约束，可以在开发阶段捕获类型错误，提高代码质量和可维护性。

## What Changes

- 审计所有 Python 文件中的裸 dict 使用情况
- 为 API 端点、函数参数和返回值添加 Pydantic 模型类型注解
- 使用正则表达式强制检查代码中不应出现的裸 JSON 模式
- 更新现有测试确保类型安全

## Capabilities

### New Capabilities
- `json-audit-tool`: 开发一个审计工具，使用正则表达式扫描代码库中的裸 JSON 用法
- `pydantic-constraint-enforcement`: 建立 Pydantic 模型约束机制，强制要求特定场景必须使用类型模型

### Modified Capabilities
- 无现有 spec 需要修改

## Impact

- 影响所有 Python 模块，特别是 `core/`、`interfaces/` 和 `managers/`
- 可能需要更新 FastAPI 路由以使用 Pydantic 响应模型
- 测试文件需要添加类型检查验证
