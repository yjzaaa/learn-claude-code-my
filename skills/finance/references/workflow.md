# 工作流说明（finance skill）

## 目标

把 finance 技能固定为“文档驱动 + 单执行脚本”模式，减少 SQL 生成漂移和执行风险。

## 标准流程

1. 读取规则与模板
   - 读取 `references/metadata.md`、`references/react_rules.md`、`references/react_constraints.md`。
   - 若需要字段级结构，再读取 `references/schema_query_guide.md`。

2. 查询表结构与示例数据
   - 先查询候选表结构（字段名、类型、可空）。
   - 再查询每张候选表的少量样例数据（如 TOP 5/10）。
   - 目的：确认字段语义、取值形态与过滤条件可行性。

3. 术语归一化
   - 把用户口语映射为标准值（例如 `预算 -> Budget1`，`实际 -> Actual`）。

4. Todo 计划与状态更新
   - 多步骤任务先调用 `todo` 建立任务清单。
   - 每个关键步骤结束后更新状态（`pending -> in_progress -> completed`）。
   - 若出现 `<reminder>Update your todos.</reminder>`，必须优先更新 `todo`。

5. 基于模板构造 SQL
   - 参考 `references/sql_templates.md` 选取最接近模板。
   - 产出单条 SQL（允许 CTE，不允许多语句）。

6. 执行前校验
   - 通过 `scripts/sql_query.py` 的私有校验方法检查。
   - 校验失败时返回结构化错误，模型应按原因重写 SQL。
   - 校验重点：
     - 仅允许 `SELECT`/`WITH` 查询；
     - 必须是单语句；
     - 禁止 DDL/DML/EXEC；
     - 禁止事务与过程控制语句；
     - 禁止 `SELECT INTO`；
     - 语句必须能返回结果集。
       - 分摊场景必须满足四重关联（Year/Scenario/Key/Month）与 `Function + Key` 绑定。

7. 执行 SQL
   - 只允许调用 `scripts/sql_query.py`。
   - 执行结果为结构化 JSON。

8. 结果解释
   - 用自然语言输出结论。
   - 对比类问题补充差值和变化率。

## 最终 SQL 产出链路（执行检查清单）

在提交最终 SQL 前，必须逐项自检：

1. 我是否先确定了问题类型（尤其是否为分摊场景）？
2. 我是否完成了 Scenario 归一化，并使用库内真实取值？
3. 分摊题是否已经绑定 `Function + Key`？
4. 分摊主体是否明确为 `CC` 或 `BL`，且过滤条件已落到 SQL？
5. 联接是否严格为 `Year + Scenario + Key + Month` 四重关联？
6. 是否对 `Rate` 重复粒度做了归一化/去重，避免重复乘法放大？
7. 计算路径是否为“月度 amount \* 月度 rate -> 汇总”，而不是先汇总后乘比例？
8. SQL 是否为单语句查询、可返回结果集、可直接执行？

任一问题回答为“否”，则当前 SQL 视为未完成，不得执行。

## 回退策略

- 校验失败：回到“模板构造 SQL”。
- 执行失败：根据错误信息回到“模板构造 SQL”。
- 当返回 `error.reasons` 时，优先按原因精准修复，不要盲目改写整条 SQL。
- 若命中分摊硬门槛失败（缺四重关联或缺 `allocation_key` 绑定），必须直接重生成，不允许执行当前 SQL。

## 禁止项

- 禁止调用历史脚本（`run_query.py`、`generate_alloc_sql.py`、`dynamic_skill_sql.py`、`example_overview.py`）。
- 禁止多语句 SQL。
- 禁止 DDL/DML/执行类语句。
- 禁止事务控制与 `SELECT INTO`。
