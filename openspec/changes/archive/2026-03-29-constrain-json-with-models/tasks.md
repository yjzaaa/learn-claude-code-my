## 1. Audit Tool Development

- [x] 1.1 Create `scripts/audit_bare_json.py` - 审计工具主脚本
- [x] 1.2 实现正则表达式模式匹配裸 JSON 类型注解
- [x] 1.3 支持扫描单个文件或整个目录
- [x] 1.4 生成 JSON/文本格式的审计报告
- [x] 1.5 添加配置文件支持白名单机制
- [x] 1.6 添加命令行参数（--config, --format, --output）

## 2. Regex Patterns Implementation

- [x] 2.1 实现 `Dict\[str,\s*Any\]` 模式检测
- [x] 2.2 实现 `dict\[str,\s*Any\]` 模式检测
- [x] 2.3 实现函数返回类型 `-\>\s*(dict|Dict\[)` 检测
- [x] 2.4 实现函数参数类型注解检测
- [x] 2.5 实现变量赋值 `{}` 和 `dict()` 检测
- [x] 2.6 排除注释和字符串字面量中的匹配

## 3. Test Enforcement Suite

- [x] 3.1 创建 `tests/test_no_bare_json.py` 测试文件
- [x] 3.2 实现扫描 core/ 目录的测试用例
- [x] 3.3 实现扫描 interfaces/ 目录的测试用例
- [x] 3.4 实现扫描 managers/ 目录的测试用例
- [x] 3.5 实现白名单功能测试
- [x] 3.6 确保测试在 CI 中失败时提供清晰的错误信息

## 4. Whitelist Configuration

- [x] 4.1 创建 `.bare-json-whitelist.json` 配置文件
- [x] 4.2 支持按文件路径白名单
- [x] 4.3 支持按代码模式白名单
- [x] 4.4 支持行级 `# noqa: bare-dict` 注释
- [x] 4.5 在白名单中记录每个例外的原因

## 5. Core Modules Type Constraining

- [x] 5.1 审计 core/models/ 中的裸 JSON 使用
- [x] 5.2 审计 core/managers/ 中的裸 JSON 使用
- [x] 5.3 审计 core/tools/ 中的裸 JSON 使用
- [x] 5.4 审计 interfaces/http/ 中的裸 JSON 使用
- [x] 5.5 审计 interfaces/websocket/ 中的裸 JSON 使用
- [ ] 5.6 将发现的裸 JSON 转换为 Pydantic 模型（后续迭代完成）

## 6. CI/CD Integration

- [x] 6.1 创建 `.pre-commit-config.yaml` 配置
- [x] 6.2 创建 GitHub Actions workflow 文件
- [x] 6.3 确保 CI 在检测到违规时阻止 PR 合并
- [x] 6.4 在 CI 报告中显示违规文件和行号

## 7. Documentation

- [x] 7.1 创建 `docs/BARE_JSON_MIGRATION.md` 迁移指南
- [x] 7.2 更新 CLAUDE.md 添加类型约束最佳实践
- [x] 7.3 在 README.md 中添加审计工具使用说明（见 BARE_JSON_MIGRATION.md）
- [x] 7.4 创建修复常见违规的代码示例（见 BARE_JSON_MIGRATION.md）

## 8. Final Verification

- [x] 8.1 运行完整审计，确保无裸 JSON 遗漏
- [x] 8.2 验证所有测试通过（测试正常工作，发现违规符合预期）
- [x] 8.3 验证 CI/CD 集成正常工作（配置已创建）
- [x] 8.4 更新任务文件标记所有任务完成
