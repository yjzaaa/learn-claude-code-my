## Why

代码库中存在大量裸 JSON/dict 类型的使用（如 `Dict[str, Any]`、`dict[str, Any]`、`-> dict` 等），这导致：
1. 类型不安全，无法在编译时捕获错误
2. 前后端数据模型不一致
3. 缺乏 IDE 自动补全和类型检查支持

需要使用 Pydantic BaseModel 替代裸 dict，建立统一的类型约束体系。

## What Changes

- 创建审计工具 `scripts/audit_bare_json.py` 扫描代码库中的裸 JSON 使用
- 创建测试 `tests/test_no_bare_json.py` 强制检查新代码不包含裸 dict
- 为核心模块添加 `# noqa: bare-dict` 标记（临时方案）
- 使用 Pydantic 模型替换裸 dict（长期方案）

## Capabilities

### New Capabilities
- `bare-json-audit`: 代码库裸 JSON 审计工具和 CI 检查

### Modified Capabilities
- 无（此 change 主要是代码质量改进，不修改功能需求）

## Impact

- 所有 `core/` 和 `interfaces/` 模块中的 Python 文件
- 开发工作流：新增 pre-commit 检查
- CI/CD：测试套件中新增类型约束检查
