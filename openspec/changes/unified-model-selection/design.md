## Context

当前模型选择系统的问题：

1. **配置逻辑复杂**：`_detect_provider_from_env()` 按固定优先级检查 API keys，无法正确处理多 provider 配置
2. **模型标识不一致**：前端使用 `deepseek-reasoner`，后端流式响应显示 `ls_provider: anthropic, ls_model_name: deepseek-reasoner`
3. **验证逻辑不可靠**：`_validate_api_key()` 使用 HTTP 请求验证，存在 SSL 问题和超时风险
4. **Base URL 推断混乱**：ANTHROPIC_BASE_URL 指向 Kimi 时，系统无法正确识别实际 provider

## Goals / Non-Goals

**Goals:**
- 简化模型配置：MODEL_ID 作为唯一必需的配置项
- 统一模型标识：所有组件使用相同的模型 ID 格式
- 可靠的多模型支持：正确检测所有配置了 API key 的 provider
- 移除复杂的 API 验证：依赖配置正确性而非运行时验证

**Non-Goals:**
- 不实现模型能力检测（如 context window、pricing）
- 不修改 LLM 调用逻辑（保持 LiteLLM/Anthropic 适配层不变）
- ~~不实现前端动态切换 provider（由后端可用模型决定）~~ → 支持前端动态选择模型

## Decisions

### 1. 简化 Provider 检测逻辑
**Decision**: 移除 `_detect_provider_from_env()` 的优先级检查，改为检测所有配置了 API key 的 provider。

**Rationale**:
- 原逻辑按固定优先级（anthropic > deepseek > openai > kimi）只返回第一个匹配的 provider
- 无法支持多 provider 同时配置的场景
- 新逻辑返回所有配置了 key 的 provider，由 MODEL_ID 决定使用哪个

**Alternative Considered**: 保留优先级但增加多 provider 支持 → 过于复杂，不如直接检测所有

### 2. 模型标识统一使用 MODEL_ID 格式
**Decision**: 所有组件统一使用 `provider/model-name` 或 `model-name` 格式。

**Rationale**:
- LiteLLM 使用 `provider/model-name` 格式（如 `deepseek/deepseek-reasoner`）
- MODEL_ID 是用户显式配置的值，应该作为唯一标识
- 避免内部转换导致的标识不一致

### 3. 移除运行时 API 验证
**Decision**: 移除 `_validate_api_key()` 的 HTTP 验证，改为直接信任 .env 配置。

**Rationale**:
- HTTP 验证存在网络超时、SSL 问题等不可靠因素
- 用户明确配置了 API key，应该视为有意使用
- 验证失败应通过 LLM 调用失败体现，而非预选时隐藏

**Risk**: 配置错误的 API key 会导致运行时错误 → 通过清晰的错误日志帮助用户诊断

### 4. Base URL 仅作为 endpoint，不用于推断 provider
**Decision**: Provider 由 API key 的名称决定（ANTHROPIC_API_KEY → anthropic），Base URL 仅修改 endpoint。

**Rationale**:
- 当前混淆源于试图从 Base URL 推断 provider
- 兼容场景（ANTHROPIC_API_KEY + Kimi URL）应显式声明为使用 anthropic 格式调用
- 简化 mental model：Key 决定身份，URL 决定地址

### 5. 客户端类型检测（关键发现）
**Decision**: ProviderManager 必须根据模型和端点检测应该使用的客户端类型（ChatLiteLLM vs ChatAnthropic）。

**Rationale**:
- 测试发现：**DeepSeek** 使用 ChatLiteLLM（OpenAI 兼容格式）
- 测试发现：**Kimi** 必须使用 ChatAnthropic（Anthropic 兼容端点），ChatLiteLLM 会失败
- 客户端类型是模型配置的一部分，必须在发现阶段确定

**实现策略**:
```python
# 测试阶段：尝试 ChatLiteLLM，失败则尝试 ChatAnthropic
# 发现成功后，记录 client_type 到配置中
{
    "model": "kimi-k2-coding",
    "client_type": "ChatAnthropic",  # 由测试确定
    "api_key": "...",
    "base_url": "..."
}
```

**参考实现**:
- `test_deep_with_discovered_models.py` 中的 `_try_chatlitellm()` 和 `_try_chatanthropic()`
- 测试逻辑：先尝试 ChatLiteLLM，流式调用失败则回退到 ChatAnthropic

### 6. 自由发现可联通模型配置
**Decision**: ProviderManager 应该主动测试 .env 中所有配置，返回实际可联通的模型列表。

**Rationale**:
- 仅检查 API key 存在不能保证连通性
- 需要实际调用测试验证模型可用性
- 前端应该只显示后端确认可用的模型

**实现策略**:
1. 从 .env 读取所有 API key（只读非注释行）- 参考 `test_freeform_provider_discovery.py`
2. 为每个 key 测试代表性模型列表
3. 并行测试所有组合，记录响应时间
4. 返回所有成功连通的模型配置

**参考实现**:
- `test_freeform_provider_discovery.py` - 从 .env 读取并测试所有配置
- `test_deep_with_discovered_models.py` - 测试模型在 deep.py 上下文中的可用性

### 7. 支持前端动态模型选择
**Decision**: 系统支持前端用户选择任意可用模型，后端根据选择动态切换模型实例。

**Rationale**:
- 用户需要针对不同对话使用不同模型（如 DeepSeek-R1 用于推理，Kimi 用于代码）
- 每个对话应该有独立的模型配置，而非全局 MODEL_ID 决定
- 模型选择应该保存在 Dialog 级别

**实现策略**:
1. **Dialog 级别模型存储**: Dialog 模型添加 `selected_model_id` 字段
2. **动态模型实例创建**: ProviderManager 提供 `get_model_for_dialog(dialog_id)` 方法
3. **切换模型流程**:
   - 前端选择模型 → POST `/api/dialogs/{id}/model`
   - 后端更新 dialog 的 `selected_model_id`
   - 后续对话使用新选择的模型
4. **默认模型**: 新对话使用 MODEL_ID 作为默认模型

## Risks / Trade-offs

- **[Risk]** 用户配置了错误的 API key，运行时才发现 → **[Mitigation]** 清晰的错误日志和错误提示
- **[Risk]** 多 provider 配置时，用户不清楚实际使用哪个 → **[Mitigation]** 前端显示当前激活的 provider 和 model
- **[Trade-off]** 移除 API 验证降低了确定性，但提高了可靠性和响应速度

## Migration Plan

1. **ProviderManager Discovery Layer**
   - 实现 `discover_credentials()` 从 .env 读取配置（参考 `test_freeform_provider_discovery.py:discover_all_credentials()`）
   - 实现 `test_model_connectivity()` 测试连通性（参考 `test_deep_with_discovered_models.py:test_model_in_deep_context()`）
   - 实现 `detect_client_type()` 检测客户端类型（参考 `test_deep_with_discovered_models.py:_try_chatlitellm()` 和 `_try_chatanthropic()`）
   - 缓存发现结果避免重复测试

2. **ProviderManager Factory Layer**
   - 实现 `create_model_instance(model_id)` 返回可直接使用的模型
   - 实现 `get_model_for_dialog(dialog_id)` 根据对话选择动态返回模型
   - 根据 client_type 选择 ChatLiteLLM 或 ChatAnthropic
   - 处理模型创建错误

3. **Dialog Model Storage**
   - 更新 Dialog 模型添加 `selected_model_id` 字段
   - 实现模型切换 API `POST /api/dialogs/{id}/model`
   - 新对话默认使用 MODEL_ID

4. **Backend API Updates**
   - 更新 `/api/config/models` 返回测试确认可用的模型
   - 添加 `POST /api/dialogs/{id}/model` 切换模型端点
   - 添加 `client_type` 字段到响应

5. **Frontend Updates**
   - 修复模型选择器使用新的 API 格式
   - 只显示后端确认可用的模型
   - 实现模型切换功能
   - 显示当前对话使用的模型

6. **Testing**
   - 验证 DeepSeek 模型通过 ChatLiteLLM 工作
   - 验证 Kimi 模型通过 ChatAnthropic 工作
   - 验证动态模型切换功能
   - 验证多 provider 配置场景

## Open Questions (Answered by Testing)

- ~~是否需要支持用户在前端切换 model（而非仅由 MODEL_ID 决定）？~~
  - **Answered**: Yes, 后端返回所有可用模型，前端让用户选择，每个 Dialog 独立存储选择

- ~~如何处理同一 provider 的多个模型（如 DeepSeek V3 和 R1）？~~
  - **Answered**: 每个模型独立测试连通性，分别返回，用户可在前端切换

- ~~如何确定使用 ChatLiteLLM 还是 ChatAnthropic？~~
  - **Answered**: 通过实际测试确定，记录 client_type 到配置中

- ~~模型切换是否立即生效？~~
  - **Answered**: Yes, 通过 `POST /api/dialogs/{id}/model` 切换后立即生效
