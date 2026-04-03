## 1. 审计工具

- [x] 1.1 创建 `scripts/audit_bare_json.py` 扫描工具
- [x] 1.2 实现 `Dict[str, Any]` 和 `dict[str, Any]` 检测
- [x] 1.3 实现裸字典字面量 `{}` 检测
- [x] 1.4 实现多行字典字面量检测
- [x] 1.5 添加 f-string 和 logger 占位符过滤
- [x] 1.6 添加 `# noqa: bare-dict` 白名单支持

## 2. 测试套件

- [x] 2.1 创建 `tests/test_no_bare_json.py` 强制检查测试
- [x] 2.2 实现 core/ 目录扫描测试
- [x] 2.3 实现 interfaces/ 目录扫描测试
- [x] 2.4 实现 managers/ 目录扫描测试
- [x] 2.5 添加白名单功能测试

## 3. Core 模块修复

- [x] 3.1 修复 `core/managers/` 模块违规
- [x] 3.2 修复 `core/hitl/` 模块违规
- [x] 3.3 修复 `core/models/` 模块违规
- [x] 3.4 修复 `core/agent/` 模块违规
- [x] 3.5 修复 `core/tools/` 模块违规
- [x] 3.6 使用 Pydantic 模型替换裸 dict（长期任务）

## 4. Interfaces 模块修复

- [x] 4.1 修复 `interfaces/websocket/` 模块违规
- [x] 4.2 修复 `interfaces/http/` 模块违规
- [x] 4.3 修复 `interfaces/agent_runtime_bridge.py` 违规

## 5. 多行字典审计工具

- [x] 5.1 创建 `scripts/audit_multiline_dict.py` 审计脚本
- [x] 5.2 集成到 `.claude/hooks/quality-gates.sh`
- [x] 5.3 创建 `ToolStartData` Pydantic 模型
- [x] 5.4 创建 `OpenAIToolCall` / `OpenAIFunction` Pydantic 模型

## 6. CI/CD 集成

- [x] 6.1 添加 pre-commit hook
- [x] 6.2 配置 GitHub Actions 检查
- [x] 6.3 更新开发者文档
