## Context

当前代码库存在大量裸 dict 类型使用，主要集中在：
- `core/models/` - 模型定义中的 `Dict[str, Any]` 类型
- `core/agent/runtimes/` - Runtime 中的字典字面量
- `core/tools/` - 工具注册和调用的字典参数

这些裸 dict 使得类型检查无法发挥作用，也容易导致运行时错误。

## Goals / Non-Goals

**Goals:**
1. 创建自动化审计工具检测裸 dict 使用
2. 创建 CI 检查防止新的裸 dict 被引入
3. 为现有代码添加 noqa 标记（短期方案）
4. 逐步使用 Pydantic 模型替换裸 dict（长期方案）

**Non-Goals:**
1. 一次性替换所有裸 dict（采用渐进式改进）
2. 修改 LangChain 相关的消息格式（保持兼容性）
3. 引入复杂的类型系统（保持简单实用）

## Decisions

**1. 使用 `# noqa: bare-dict` 标记而非立即重构**
- 理由：现有代码量太大，一次性重构风险高
- 标记后可以在代码审查中识别需要改进的地方

**2. 审计工具使用正则表达式而非 AST**
- 理由：实现简单，运行快速，足以检测常见模式
- 权衡：可能误报 f-string 中的 `{}`，已添加特殊处理

**3. 测试套件强制检查而非仅警告**
- 理由：防止新代码引入裸 dict
- 失败的测试会阻止代码合并

**4. 专门的多行字典字面量审计**
- 理由：多行字典字面量是最需要优先替换的，因为它们通常表示复杂的数据结构
- 创建了 `scripts/audit_multiline_dict.py` 专门检测此类问题
- 集成到 `.claude/hooks/quality-gates.sh` 在 Quality Gates 中强制执行
- 白名单标记：`# noqa: multiline-dict`

## Risks / Trade-offs

**Risk**: 过多的 noqa 标记可能掩盖真正的问题
- Mitigation: 定期审查 noqa 标记的代码，逐步重构

**Risk**: 审计工具可能误报
- Mitigation: 工具已添加 f-string 和 logger 占位符检测

**Risk**: 开发体验下降（需要处理更多类型错误）
- Mitigation: 提供清晰的错误信息和修复建议
