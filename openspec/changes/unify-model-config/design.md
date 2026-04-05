## Context

当前代码库中模型配置散落在多个位置：

1. **ProviderManager** (`provider_manager.py`): 从环境变量获取 API key，但模型选择逻辑分散
2. **DeepAgentRuntime** (`deep.py:180`): 硬编码 `os.getenv("MODEL_ID", "kimi-k2-coding")`
3. **EngineConfig** (`config.py:37`): 默认 `model: str = "deepseek/deepseek-chat"`
4. **LiteLLMProvider** (`litellm.py:40`): 默认 `default_model: str = "deepseek/deepseek-chat"`
5. **多处测试代码**: 各自从环境变量获取 MODEL_ID

这种分散导致：
- 配置不一致（不同地方不同默认值）
- 难以切换模型（需要修改多处）
- 新开发者不清楚配置入口

## Goals / Non-Goals

**Goals:**
- 单一配置入口：`.env` 文件决定模型配置
- ProviderManager 成为唯一配置管理中心
- 移除所有硬编码默认模型值
- 向后兼容：环境变量方式不变

**Non-Goals:**
- 不支持运行时动态切换模型（未来可扩展）
- 不修改 Provider 实现细节（LiteLLM/OpenAI 适配器）
- 不修改前端配置方式

## Decisions

### 1. 配置优先级
- **第一优先级**: `MODEL_ID` 环境变量
- **第二优先级**: 特定 Provider 变量（如 `ANTHROPIC_MODEL`, `DEEPSEEK_MODEL`）
- **第三优先级**: ProviderManager 根据 API key 推断默认模型

**Rationale**: 保持简单，绝大多数用户只需要设置 `MODEL_ID` 和对应的 `API_KEY`。

### 2. ProviderManager 职责扩展
ProviderManager 不仅管理 Provider 实例，还负责：
- 从环境变量解析模型配置
- 提供统一的 `get_model_config()` 接口
- 缓存配置避免重复读取

**Rationale**: 这是架构上最自然的放置点，已有 Provider 管理职责。

### 3. 向后兼容
- 保留 `MODEL_ID` 环境变量名
- 保留 `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY` 等变量名
- 默认模型推断逻辑不变（根据哪个 key 存在）

**Rationale**: 避免破坏现有部署。

## Risks / Trade-offs

**[Risk]** 修改配置获取路径可能引入回归 → **Mitigation**: 保持环境变量名不变，添加单元测试

**[Risk]** 移除硬编码默认值可能导致未设置环境变量时报错 → **Mitigation**: ProviderManager 保留智能推断逻辑（根据 API key 推断默认模型）

**[Trade-off]** 配置集中后，Study 目录的独立示例可能需要额外导入 → 接受此代价，Study 代码保持简单示例性质
