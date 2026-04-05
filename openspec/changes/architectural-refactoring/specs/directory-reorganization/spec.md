## ADDED Requirements

### Requirement: 日志文件必须按类别组织
系统 SHALL 将日志文件组织到分类目录中。

#### Scenario: 运行时日志目录
- **WHEN** 检查 `logs/runtime/` 目录
- **THEN** 它 SHALL 包含 agent 运行时日志
- **AND** `logs/deep/raw_event.jsonl` SHALL 移动到此处

#### Scenario: 调试日志目录
- **WHEN** 检查 `logs/debug/` 目录
- **THEN** 它 SHALL 包含调试和跟踪日志
- **AND** `logs/session_debug.jsonl` SHALL 移动到此处

#### Scenario: 连通性测试日志目录
- **WHEN** 检查 `logs/connectivity/` 目录
- **THEN** 它 SHALL 包含模型连通性测试结果
- **AND** 现有连通性日志 SHALL 保留在此处

#### Scenario: 快照目录
- **WHEN** 检查 `logs/snapshots/` 目录
- **THEN** 它 SHALL 包含 checkpoint 快照
- **AND** 现有快照文件 SHALL 保留在此处

### Requirement: 中间件必须按功能分组
系统 SHALL 将中间件文件按功能组织到子目录中。

#### Scenario: 压缩中间件分组
- **WHEN** 检查 `backend/infrastructure/runtime/middleware/compression/` 目录
- **THEN** 它 SHALL 包含 `claude_compression.py`
- **AND** 相关压缩工具 SHALL 移动至此

#### Scenario: 缓存中间件分组
- **WHEN** 检查 `backend/infrastructure/runtime/middleware/caching/` 目录
- **THEN** 它 SHALL 包含 prompt caching 相关中间件

#### Scenario: 工具中间件分组
- **WHEN** 检查 `backend/infrastructure/runtime/middleware/tools/` 目录
- **THEN** 它 SHALL 包含工具调用相关中间件

### Requirement: 测试文件必须按类别组织
系统 SHALL 将测试文件按类别组织。

#### Scenario: 单元测试目录
- **WHEN** 检查 `tests/unit/` 目录
- **THEN** 它 SHALL 包含单元测试

#### Scenario: 集成测试目录
- **WHEN** 检查 `tests/integration/` 目录
- **THEN** 它 SHALL 包含集成测试

#### Scenario: 端到端测试目录
- **WHEN** 检查 `tests/e2e/` 目录
- **THEN** 它 SHALL 包含端到端测试

### Requirement: 目录迁移必须保持向后兼容
系统 SHALL 确保目录迁移不影响现有功能。

#### Scenario: 配置更新
- **WHEN** 检查代码中的日志路径
- **THEN** 所有路径 SHALL 更新为新目录结构
- **AND** 不应有引用旧路径的硬编码

#### Scenario: .gitignore 更新
- **WHEN** 检查 `.gitignore` 文件
- **THEN** 它 SHALL 包含新的日志目录模式
- **AND** 旧模式可以移除
