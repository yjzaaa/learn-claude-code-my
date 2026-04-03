## Why

当前的 `SimpleRuntime` 和 `DeepRuntime` 中嵌入了大量的业务逻辑，包括：

1. **系统提示词构建逻辑** (`_build_system_prompt()`) - 硬编码在 runtime 中
2. **工作区工具注册** (`setup_workspace_tools()`) - 与 WorkspaceOps 耦合
3. **记忆管理** - 直接与 MemoryManager 交互
4. **HITL API** - 与 skill_edit_hitl_store 和 todo_store 耦合

这种设计导致：
- **代码重复**: SimpleRuntime 和 DeepRuntime 各自实现相似逻辑
- **难以扩展**: 添加新的提示词组件需要修改 runtime 代码
- **业务与框架耦合**: runtime 应该专注于流程编排，而非业务细节

通过将这些业务逻辑提取为独立的 skills，可以实现：
- **可复用性**: 相同的 skill 可用于不同的 runtime
- **可配置性**: 通过配置启用/禁用特定 skill
- **可测试性**: 独立测试每个 skill 的逻辑
- **可维护性**: 业务变更无需修改 runtime 核心

## What Changes

### 提取的业务技能

1. **system-prompt-builder** - 系统提示词构建
   - 从 memory 加载长期记忆
   - 聚合已加载 skills 的提示词
   - 整合插件系统提示词

2. **workspace-tools** - 工作区操作工具
   - 文件读取/写入
   - 目录列表
   - 代码搜索等

3. **memory-manager** - 记忆管理
   - 对话总结
   - memory.md 读写
   - 长期记忆检索

4. **hitl-manager** - HITL 支持
   - Skill 编辑审核
   - Todo 列表管理

5. **dialog-lifecycle** - 对话生命周期
   - 对话创建/关闭
   - 消息处理流程

### 运行时变更

- `SimpleRuntime`: 移除硬编码业务逻辑，改为通过 skill_manager 调用
- `DeepRuntime`: 通过 skills 参数接收业务 skills
- 新增 `AgentFactory`: 自动加载和配置 skills

## Capabilities

### New Capabilities

- **可插拔的系统提示词**: 通过 skills 配置不同的提示词组件
- **可复用的工作区工具**: 任何 skill 都可以使用工作区工具
- **统一的记忆管理**: 所有 runtime 使用相同的记忆管理机制
- **标准化的 HITL**: 一致的 HITL 接口

### Modified Capabilities

- `SimpleRuntime._build_system_prompt()` → 由 system-prompt-builder skill 提供
- `SimpleRuntime.setup_workspace_tools()` → 由 workspace-tools skill 提供
- `SimpleRuntime.close_dialog()` 中的记忆总结 → 由 memory-manager skill 提供
- HITL API → 由 hitl-manager skill 提供

## Impact

- **代码影响**: runtime 文件将大幅简化，业务逻辑迁移到 skills 目录
- **API 影响**: 无，外部 API 保持不变
- **配置影响**: 新增 `SKILL_DIR` 等环境变量配置
- **测试影响**: 需要为每个 skill 编写独立测试

## Dependencies

- 依赖: 现有 skill 系统 (`core.managers.skill_manager`)
- 依赖: `core/tools/WorkspaceOps` 工具集
- 依赖: `core/hitl/` HITL 系统
