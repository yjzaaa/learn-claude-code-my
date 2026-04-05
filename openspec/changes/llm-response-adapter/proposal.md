## Why

当前系统需要支持多种 LLM 提供商（Claude、DeepSeek、Kimi 等），但不同提供商的响应数据结构差异很大。前端需要统一的接口来消费思考过程、token 用量、模型名称等元数据。我们需要一个适配层来标准化这些多样化的响应格式。

## What Changes

- 新增 LLM Response Adapter 模块，统一处理不同提供商的原始响应
- 支持提取思考过程（reasoning_content）
- 支持提取 token 用量（input/output/total tokens）
- 支持提取模型名称和版本信息
- 支持流式响应的增量数据解析
- 统一的响应数据模型，前端可消费

## Capabilities

### New Capabilities
- `llm-response-adapter`: 核心适配器，将不同 LLM 的原始响应转换为统一格式
- `llm-metadata-extractor`: 元数据提取器，处理 token 用量、模型信息等
- `llm-streaming-parser`: 流式响应解析器，处理增量数据流

### Modified Capabilities
- 无（此变更是新增能力，不涉及现有 spec 修改）

## Impact

- 后端: 新增适配层模块，修改 DeepAgentRuntime 和 SimpleAgentRuntime 使用适配器
- 前端: 可使用统一的响应数据结构，无需处理不同 LLM 的差异
- API: WebSocket 事件数据结构将标准化
