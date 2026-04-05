## Context

当前系统支持多种 LLM 提供商（通过 LiteLLM 和 DeepAgents），但每个提供商的响应格式差异很大：

- **Claude**: 使用 `additional_kwargs.reasoning_content`，token 在 `usage` 字段
- **DeepSeek**: 使用 `reasoning_content` 字段，token 格式与 OpenAI 兼容
- **Kimi**: 使用 `reasoning_content` 字段，但有独特的响应结构
- **OpenAI**: 标准格式，可能包含 `system_fingerprint`

前端需要统一的接口来展示这些信息，目前代码中散落着针对不同提供商的特殊处理逻辑。

## Goals / Non-Goals

**Goals:**
- 创建统一的 LLM 响应适配层，支持所有主流提供商
- 标准化提取思考过程、token 用量、模型信息
- 支持流式和非流式两种模式
- 定义前端可消费的统一数据模型
- 将提供商特定的解析逻辑集中管理

**Non-Goals:**
- 不修改底层 LLM 调用方式（仍使用 LiteLLM/DeepAgents）
- 不改变前端 UI 展示逻辑（只提供标准化数据）
- 不支持非标准/自定义 LLM 提供商（只覆盖主流）

## Decisions

**1. 适配器架构模式**
- 使用策略模式（Strategy Pattern），每个提供商一个适配器
- 统一接口 `LLMResponseAdapter`，所有适配器实现此接口
- 工厂模式创建对应提供商的适配器

**2. 统一数据模型设计**
```python
class UnifiedLLMResponse:
    content: str                          # 主响应内容
    reasoning_content: Optional[str]    # 思考过程
    model: str                          # 模型名称
    usage: TokenUsage                   # token 用量
    provider: str                       # 提供商标识
    metadata: Dict[str, Any]           # 扩展字段
```

**3. 流式处理策略**
- 增量解析器负责将流式 chunk 累积并解析
- 每次 chunk 都尝试提取增量信息
- 最终统一格式化后广播给前端

**4. 错误处理策略**
- 解析失败时返回原始内容，不阻断流程
- 记录警告日志，便于排查
- 提供 fallback 适配器处理未知格式

## Risks / Trade-offs

- **新适配器维护成本** → 定义清晰的适配器接口，新提供商只需实现接口
- **性能开销** → 解析逻辑轻量，只做字段映射不涉及 heavy computation
- **格式变更风险** → 提供商 API 变更时适配器需更新，但影响范围可控

## Migration Plan

1. 创建适配器基础设施（接口、工厂、基础实现）
2. 为 Claude/DeepSeek/Kimi 实现具体适配器
3. 修改 DeepAgentRuntime 使用适配器
4. 测试验证所有提供商响应格式
5. 前端消费新数据结构

## Open Questions

- 是否需要缓存适配器实例？
- 流式响应的 token 统计如何处理（部分提供商只在最后返回 usage）？
