## Why

当前的模型选择系统存在严重的逻辑混乱：
1. 前端显示的模型列表与后端实际可用的模型不匹配
2. 环境变量配置（ANTHROPIC_API_KEY + ANTHROPIC_BASE_URL 指向 Kimi）与预期行为不符
3. 模型验证逻辑复杂且不可靠，导致用户无法正确选择可用模型
4. 模型元数据（provider、model_name）在流式响应中不一致

需要重构为一个简单、可靠的统一模型选择系统，确保前端、后端和 LLM 调用使用一致的模型标识。

## What Changes

- **重构 ProviderManager**：实现发现式模型检测，主动测试所有配置返回可用模型列表
- **客户端类型检测**：自动检测每个模型应使用 ChatLiteLLM（DeepSeek）还是 ChatAnthropic（Kimi）
- **统一模型标识**：确保所有组件（前端、后端、LLM 调用）使用相同的模型 ID 格式
- **模型实例工厂**：根据模型 ID 返回可直接使用的模型实例（已确定客户端类型）
- **支持动态模型切换**：前端选择模型后，后端根据选择动态切换模型实例
- **Dialog 级别模型存储**：每个对话独立存储所选模型，不同对话可使用不同模型
- **修复前端模型选择器**：下拉框只显示后端确认可用的模型，支持实时切换
- **修复模型元数据**：确保流式响应中的 model_provider 和 model_name 与实际使用的模型一致

## Capabilities

### New Capabilities
- `model-discovery`: 自动发现 .env 中所有可联通的模型配置
- `client-type-detection`: 自动检测模型应使用的客户端类型（ChatLiteLLM vs ChatAnthropic）
- `model-instance-factory`: 根据模型 ID 返回可直接使用的模型实例
- `dynamic-model-switching`: 支持前端动态选择模型，后端实时切换
- `dialog-level-model-storage`: Dialog 级别模型存储，不同对话使用不同模型
- `unified-model-config`: 统一的模型配置管理，以 MODEL_ID 为默认配置源

### Modified Capabilities
- `provider-manager`: 简化 provider 检测逻辑，移除复杂的 base_url 推断
- `model-selection-ui`: 修复前端模型选择器，确保显示正确的可用模型列表

## Impact

- **Backend**: ProviderManager、agent runtime、model adapter
- **Frontend**: InputArea 组件的模型选择器
- **API**: `/api/config/models` 端点返回格式
- **Configuration**: .env 文件配置方式简化
