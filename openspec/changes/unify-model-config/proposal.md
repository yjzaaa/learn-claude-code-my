## Why

代码库中模型配置散落在多个地方（ProviderManager、DeepAgentRuntime、config.py、litellm.py 等），导致配置不一致且难以维护。需要统一模型配置管理，由 .env 单一来源决定，避免硬编码默认值。

## What Changes

- **新增**: `ModelConfig` 配置类，统一管理模型名称、Provider、API 密钥等
- **修改**: `ProviderManager` 成为模型配置的唯一管理中心
- **修改**: `DeepAgentRuntime` 从 ProviderManager 获取模型配置，移除硬编码
- **修改**: `EngineConfig` 和 `ProviderConfig` 整合到统一配置体系
- **修改**: `.env.example` 添加清晰的模型配置选项
- **BREAKING**: 移除散落在各处的默认模型硬编码值

## Capabilities

### New Capabilities
- `unified-model-config`: 统一模型配置管理，支持通过环境变量配置模型

### Modified Capabilities
- (none - 这是内部重构，不修改外部行为)

## Impact

- `backend/infrastructure/services/provider_manager.py` - 成为配置中心
- `backend/infrastructure/runtime/deep.py` - 移除硬编码模型获取
- `backend/domain/models/shared/config.py` - 整合配置类
- `backend/infrastructure/providers/litellm.py` - 移除默认模型硬编码
- `.env.example` - 添加配置文档
- 测试文件 - 更新模型获取方式
