# Skill Engine 详细规格（参考 OpenSpace）

## OpenSpace Skill Engine 核心机制分析

### 1. 三层监控体系

```
┌─────────────────────────────────────────────────────┐
│  Layer 3: Quality Monitor (质量监控层)               │
│  - 追踪 Skill 成功率、Token 效率、执行耗时            │
│  - 触发修复/优化流程                                 │
├─────────────────────────────────────────────────────┤
│  Layer 2: Pattern Extractor (模式提取层)             │
│  - 从执行记录提取结构化模式                          │
│  - 识别错误签名和解决方案                            │
├─────────────────────────────────────────────────────┤
│  Layer 1: Execution Recorder (执行记录层)            │
│  - 记录完整执行上下文                                │
│  - 工具调用链追踪                                    │
└─────────────────────────────────────────────────────┘
```

### 2. Auto-Fix 机制

**触发条件**:
- Skill 执行抛出异常
- 返回值不符合预期 Schema
- 连续 N 次执行失败

**修复流程**:
```python
class SkillFixer:
    def fix(self, skill: Skill, error: ExecutionError) -> FixResult:
        # 1. 分析错误类型
        error_type = self.classify_error(error)

        # 2. 查询历史修复模式
        patterns = self.pattern_repo.find_by_error(error_type)

        # 3. 尝试应用修复
        for pattern in patterns:
            patched_skill = self.apply_patch(skill, pattern)
            if self.validate(patched_skill):
                return FixResult(skill=patched_skill, pattern=pattern)

        # 4. 无匹配模式，LLM 生成修复
        return self.llm_generate_fix(skill, error)
```

**错误分类**:
| 错误类型 | 示例 | 修复策略 |
|---------|------|---------|
| ImportError | 模块未找到 | 更新依赖/修改导入 |
| APIChange | API 响应格式变更 | 更新解析逻辑 |
| SchemaMismatch | 返回格式不符 | 更新输出校验 |
| TimeoutError | 执行超时 | 添加重试/优化逻辑 |
| AuthError | 认证失败 | 更新凭证获取 |

### 3. Auto-Improve 机制

**改进维度**:
- **Prompt 优化** - 基于成功案例提炼更清晰的指令
- **参数调优** - 找到最优参数组合
- **工具链简化** - 减少不必要的工具调用

**改进流程**:
```python
class SkillImprover:
    def improve(self, skill_name: str) -> ImprovementResult:
        # 1. 获取近期执行记录
        records = self.log_repo.get_recent(skill_name, limit=100)

        # 2. 对比成功/失败案例
        successful = [r for r in records if r.success]
        failed = [r for r in records if not r.success]

        # 3. 提取成功模式
        patterns = self.extract_patterns(successful)

        # 4. 生成改进版本
        improved = self.generate_improved_skill(skill_name, patterns)

        # 5. A/B 测试验证
        return self.ab_test(improved, baseline=skill_name)
```

### 4. Auto-Learn 机制

**学习场景**:
- Agent 完成复杂任务后，提取可复用步骤
- 多个相似任务的共同模式
- 用户手动优化的 Skill 变体

**学习流程**:
```python
class SkillLearner:
    def learn_from_dialog(self, dialog_id: str) -> Optional[Skill]:
        # 1. 获取对话完整记录
        dialog = self.dialog_repo.get(dialog_id)

        # 2. 识别重复模式
        repeated_steps = self.identify_repeated_patterns(dialog)

        # 3. 判断是否值得封装为 Skill
        if not self.worth_extracting(repeated_steps):
            return None

        # 4. 生成 Skill 草案
        draft_skill = self.generate_skill(repeated_steps)

        # 5. 命名和分类
        draft_skill.name = self.generate_name(draft_skill)
        draft_skill.category = self.classify(draft_skill)

        return draft_skill
```

## 与当前项目集成方案

### 关键适配点

1. **DeepAgentRuntime 扩展**
   - 在 `ToolManagerMixin` 中注入执行记录
   - 在 `StopHandlerMixin` 中捕获异常

2. **EventBus 扩展**
   - 新增领域事件：`SkillExecuted`, `SkillFailed`, `SkillEvolved`

3. **Skill 元数据扩展**
   ```python
   class SkillMeta:
       name: str
       version: str = "1.0.0"
       evolution_info: EvolutionInfo  # 新增

   class EvolutionInfo:
       created_from: Optional[str]    # 父版本
       evolution_count: int           # 进化次数
       success_rate: float            # 成功率
       avg_token_usage: int           # 平均 Token
       last_fixed_at: Optional[datetime]
       improvement_history: List[ImprovementRecord]
   ```

## 实施路线图

### Phase 1: 基础监控 (Week 1-2)
- 执行记录存储
- 基础成功率统计

### Phase 2: 自动修复 (Week 3-4)
- 常见错误模式识别
- LLM 辅助修复

### Phase 3: 自动优化 (Week 5-6)
- Prompt 优化
- 参数调优

### Phase 4: 自动学习 (Week 7-8)
- 模式提取
- 新 Skill 生成
