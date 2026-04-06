## Why

当前项目的 Skill Engine 采用简单关键词匹配，存在以下问题：
1. **发现准确率有限** - 字面匹配无法捕获语义相似（如"finance"和"investment"）
2. **缺乏容错机制** - 技能失败即任务失败，无自动降级
3. **无质量反馈** - 无法识别低效技能，选择依赖运气
4. **技能无进化** - 失败经验无法转化为技能改进

参考 OpenSpace 的设计理念，需要构建一个自优化、高容错的 Skill Engine，通过 BM25+Embedding 混合排序提升发现准确率，通过两阶段执行确保任务完成，通过质量追踪和进化实现自我改进。

## What Changes

- **新增** `SkillEngineMiddleware` - LangChain AgentMiddleware 实现，深度集成技能生命周期
- **新增** BM25 + Embedding 混合排序技能发现机制（`SkillRanker`）
- **新增** 两阶段执行策略：Skill-First → Tool-Fallback，失败自动清理并回退
- **新增** `SkillStore` 质量追踪系统，记录选择/应用/完成/回退指标
- **新增** `.skill_id` sidecar 文件支持，实现技能 ID 持久化和版本管理
- **新增** 后端感知提示词注入，根据可用工具动态调整指导
- **新增** `SkillEvolver` 执行分析器，从失败中提取 FIX/DERIVED/CAPTURED 技能
- **重构** SkillManager 接口，与中间件深度集成
- **更新** DeepAgentRuntime 初始化流程，支持两阶段执行和后台进化

## Capabilities

### New Capabilities
- `skill-engine-middleware`: LangChain 中间件，统一处理技能生命周期、发现、注入和追踪
- `skill-ranker`: BM25 + Embedding 混合排序技能发现，带缓存和预过滤
- `skill-context-discovery`: 语义化技能匹配，支持向量相似度
- `skill-two-phase-execution`: Skill-First → Tool-Fallback 两阶段执行策略
- `skill-quality-store`: 技能质量指标追踪（选择/应用/完成/回退）
- `skill-id-sidecar`: `.skill_id` sidecar 文件持久化，支持技能版本演化
- `skill-backend-aware-injection`: 后端感知提示词注入，动态适配可用工具
- `skill-execution-analyzer`: 执行后分析，识别失败模式和进化机会
- `skill-evolver`: 技能进化引擎，自动生成 FIX/DERIVED/CAPTURED 技能

### Modified Capabilities
- `memory-middleware`: 与技能中间件协调执行顺序（Skill → Memory → User）

## Impact

- **代码位置**:
  - `backend/infrastructure/runtime/deep/middleware/skill_engine.py` - 主中间件
  - `backend/infrastructure/services/skill_ranker.py` - 混合排序
  - `backend/infrastructure/persistence/skill_store.py` - 质量存储
  - `backend/infrastructure/services/skill_evolver.py` - 进化引擎
- **接口变更**:
  - SkillManager 新增 `discover_with_ranker()`, `get_skill_quality()`, `evolve_skill()`
  - DeepAgentRuntime 新增 `_execute_skill_phase()`, `_execute_tool_fallback()`
- **配置变更**:
  - 新增 `skill.embedding.enabled`, `skill.embedding.model`, `skill.embedding.cache_dir`
  - 新增 `skill.two_phase.enabled`, `skill.two_phase.cleanup_on_fallback`
  - 新增 `skill.evolution.enabled`, `skill.evolution.max_concurrent`
- **依赖**: 新增可选依赖 `rank-bm25` 用于 BM25 排序
- **数据**:
  - `.skill_id` sidecar 文件写入技能目录
  - `skill_quality.jsonl` 记录质量指标
  - `skill_embeddings.pkl` 缓存向量
- **运行时**:
  - DeepAgentRuntime 初始化时加载 SkillRanker 和 SkillStore
  - 执行后异步触发进化任务
