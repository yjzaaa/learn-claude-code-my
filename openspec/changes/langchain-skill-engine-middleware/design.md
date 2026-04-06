## Context

### 当前架构

项目使用分层架构 (Interfaces → Application → Domain → Infrastructure)，Agent 运行时位于 `backend/infrastructure/runtime/`。DeepAgentRuntime 使用 Mixin 模式组合功能，已通过 `MemoryMiddleware` 实现了 LangChain AgentMiddleware 模式。

现有技能系统：
- `SkillManager`: 管理技能生命周期，加载 SKILL.md
- `SkillLoaderMixin`: 懒加载技能脚本
- 技能目录: `skills/<skill-name>/SKILL.md`

### OpenSpace 设计理念

OpenSpace 是 HKUDS 开发的智能体框架，其核心创新：

1. **SkillRanker**: BM25 + Embedding 混合排序，缓存 embedding 到本地
2. **两阶段执行**: Skill-First → Tool-Fallback，失败清理后回退
3. **SkillStore**: 追踪选择/应用/完成/回退指标，数据驱动过滤
4. **SkillEvolver**: 从执行分析中提取 FIX/DERIVED/CAPTURED 技能
5. **.skill_id sidecar**: 技能 ID 持久化，支持版本演化
6. **后端感知注入**: 根据可用工具动态调整提示词

## Goals / Non-Goals

**Goals:**
- 实现 BM25 + Embedding 混合排序技能发现（带本地缓存）
- 实现两阶段执行：技能阶段失败自动回退到纯工具阶段
- 建立技能质量追踪系统，自动过滤低效技能
- 实现 .skill_id sidecar 持久化，支持技能版本管理
- 实现执行分析器，识别技能改进机会
- 与现有 MemoryMiddleware 协调工作（Skill → Memory 顺序）

**Non-Goals:**
- 完整的 SkillEvolver 自动修复技能（第一阶段只做分析）
- 云端技能市场和分布式技能共享
- MCP 协议支持（当前项目使用自定义工具层）
- 多模态技能（图片/视频处理）

## Decisions

### 1. BM25 + Embedding 混合排序

**Decision**: 两阶段排序：BM25 预过滤 → Embedding 重排序

**Rationale**:
- BM25 本地计算零成本，快速缩小候选集
- Embedding 捕获语义相似，提升准确率
- 预过滤阈值 `PREFILTER_THRESHOLD = 10`，小技能集跳过 embedding 节省成本

**实现策略**:
```python
def hybrid_rank(query, candidates, top_k=10):
    # Stage 1: BM25 快速预过滤
    bm25_top = bm25_rank(query, candidates, top_k * 3)
    # Stage 2: Embedding 语义重排序
    return embedding_rank(query, bm25_top, top_k)
```

**Embedding 缓存**:
- 本地 pickle 文件 `.skill_embedding_cache/skill_embeddings_v1.pkl`
- 按 `skill_id` 索引，避免重复计算
- 技能更新时通过 `mtime` 检测并刷新

**Alternatives Considered**:
- 纯向量数据库：引入外部依赖，过度设计
- 纯 BM25：准确率不足，语义匹配差

### 2. 两阶段执行策略

**Decision**: Skill-First → Tool-Fallback，失败时清理工作区

**Rationale**:
- 技能失败不阻断任务，用户体验好
- 工作区清理确保回退阶段状态干净
- 回退阶段获得完整迭代预算（而非剩余残量）

**执行流程**:
```python
async def execute(task):
    # Phase 1: Skill-guided
    if skills_selected:
        pre_skill_files = snapshot_workspace()
        result = await agent.process_with_skills()
        
        if result.status == "success":
            return result  # 成功，直接返回
        
        # 失败：清理工作区
        cleanup_new_files(pre_skill_files)
    
    # Phase 2: Tool-only fallback
    return await agent.process_without_skills()
```

**工作区清理策略**:
- 记录技能阶段前的文件列表
- 回退前删除新增文件/目录
- 保留原始文件，避免误删用户数据

**Alternatives Considered**:
- 单阶段混合执行：技能失败难以隔离影响
- 不清理直接回退：脏状态可能误导工具阶段

### 3. 质量指标追踪

**Decision**: 追踪四个核心指标，自动过滤低效技能

**指标定义**:
- `total_selections`: LLM 选中次数
- `total_applied`: 实际应用到对话的次数
- `total_completions`: 成功完成任务次数
- `total_fallbacks`: 触发回退次数

**过滤规则**:
```python
# 规则1: 多次选中但从未完成
if selections >= 2 and completions == 0:
    filter_out(skill)

# 规则2: 应用后高回退率
if applied >= 2 and fallbacks / applied > 0.5:
    filter_out(skill)
```

**存储策略**:
- JSONL 格式 `skill_quality.jsonl`，追加写入
- 内存缓存 + 定期刷盘
- 启动时从文件加载历史数据

**Alternatives Considered**:
- 数据库存储：当前项目无技能专用 DB，JSONL 更简单
- 仅内存存储：进程重启丢失数据

### 4. .skill_id Sidecar 文件

**Decision**: 使用 `.skill_id` 文件持久化技能 ID

**ID 格式**:
- 导入技能: `{name}__imp_{uuid8}`（如 `finance__imp_a3f2b1c9`）
- 进化技能: `{name}__v{gen}_{uuid8}`（如 `finance__v2_b4e5d6f7`）

**生成策略**:
- 首次发现：读取 frontmatter 的 `name`，生成新 ID 并写入 sidecar
- 后续发现：直接读取 sidecar 中的 ID

**好处**:
- 技能目录移动不影响 ID
- 多版本技能可共存（同名不同 ID）
- 支持版本演化追踪（v1 → v2 → v3）

**Alternatives Considered**:
- 目录名作为 ID：移动后无法识别
- 文件内容 hash：微小修改即新 ID，丢失连续性

### 5. 中间件执行顺序

**Decision**: SkillEngineMiddleware 先于 MemoryMiddleware 执行

**顺序**:
```
1. SkillEngineMiddleware.abefore_model() → 发现技能、注入提示词
2. MemoryMiddleware.abefore_model() → 加载相关记忆
3. LLM 调用
4. SkillEngineMiddleware.aafter_model() → 追踪执行结果
```

**提示词层级**:
```
System Message:
  [Base System Prompt]
  [Skill Prompts]  ← Skill 中间件注入
  [Memory Context] ← Memory 中间件注入
  
User Messages...
```

**Rationale**:
- 技能作为"能力扩展"，应在系统层
- 记忆作为"上下文信息"，应在用户层
- 避免记忆覆盖技能指令

### 6. Embedding 模型选择

**Decision**: 使用 `text-embedding-3-small` 作为默认模型

**配置策略**:
```python
SKILL_EMBEDDING_MODEL = "openai/text-embedding-3-small"  # 默认
SKILL_EMBEDDING_MAX_CHARS = 12_000  # 截断长度
```

**优先级**:
1. 配置文件 `skill.embedding.model`
2. 环境变量 `OPENAI_EMBEDDING_MODEL`
3. 默认值 `text-embedding-3-small`

**文本构建**:
```python
embedding_text = f"{name}\n{description}\n\n{skill_body[:8000]}"
```

**Alternatives Considered**:
- `text-embedding-3-large`: 成本高，收益边际递减
- 本地模型：增加依赖和内存占用

### 7. 进化策略（简化版）

**Decision**: 第一阶段只实现执行分析，不做自动修复

**分析器输出**:
```python
@dataclass
class ExecutionAnalysis:
    success: bool
    error_pattern: Optional[str]  # 错误模式识别
    suggested_improvement: Optional[str]  # 改进建议
    candidate_for_evolution: bool  # 是否适合进化
```

**后续扩展**:
- Phase 2: 自动生成 FIX 技能
- Phase 3: 从成功模式提取 DERIVED 技能

**Rationale**:
- 执行分析本身有价值（识别问题）
- 自动修复风险高，需要人工审核
- 渐进式演进，降低实现复杂度

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| Embedding API 成本 | Medium | BM25 预过滤减少 70%+ 调用；本地缓存复用 |
| 两阶段执行延迟 | Low | 技能成功时跳过工具阶段；失败清理是本地 IO |
| Skill ID 冲突 | Low | UUID8 熵足够；冲突时添加计数器后缀 |
| 质量数据丢失 | Medium | JSONL 追加写入；定期备份；启动时加载 |
| 提示词过长 | Medium | 技能数量限制（max_select=2）；动态截断 |
| 中间件顺序错误 | High | 初始化时验证顺序，记录警告日志 |

## Migration Plan

### 阶段 1: 混合排序（向后兼容）
1. 创建 `SkillRanker` 类，可选依赖 `rank-bm25`
2. 配置默认关闭 embedding（`skill.embedding.enabled = false`）
3. 仅启用 BM25，无外部依赖

### 阶段 2: 两阶段执行
1. 创建 `SkillEngineMiddleware` 框架
2. 实现 Phase 1 (Skill)，Phase 2 (Fallback) 为空实现
3. 配置控制 `skill.two_phase.enabled = false`

### 阶段 3: 质量追踪
1. 创建 `SkillStore` 和 `.skill_id` sidecar
2. 写入质量数据但不用于过滤
3. 日志输出质量指标供观察

### 阶段 4: 完整功能（默认启用）
1. 启用 embedding 和质量过滤
2. 启用两阶段执行
3. 监控指标和回退率

### Rollback
- 设置 `skill.engine.enabled = false` 回退到原始行为
- `.skill_id` 文件不影响原技能加载
- 质量数据文件可安全删除

## Open Questions

1. **Embedding 服务**: 是否已有 OpenAI/兼容 API？如果没有，是否添加本地模型回退？
2. **技能数量**: 当前项目有多少技能？如果 <5 个，BM25 预过滤可能过度设计
3. **回退策略**: 两阶段执行是否适用于所有任务类型？是否需要按任务类型配置？
4. **进化审核**: 生成的 FIX/DERIVED 技能是否需要人工审核才能激活？
5. **多租户**: SkillStore 数据是按用户隔离还是全局共享？
