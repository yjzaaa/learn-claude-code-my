---
name: finance
description: Finance analytics skill with a strict workflow: read finance references, query table schema and sample rows first, then build SQL from templates, validate it, and execute only through scripts/sql_query.py.
---

# Finance Skill

## 目标

`finance` 技能只做一件事：根据财务问题生成合规 SQL，并通过唯一执行脚本 `scripts/sql_query.py` 返回结构化结果。

## 必须遵守的工作流程

1. 先读规则和模板文档，不直接“拍脑袋”写 SQL。
2. 对多步骤问题先调用 `todo` 建立任务清单（至少 3 步：需求理解、SQL 生成、结果解释）。
3. 在写业务 SQL 前，先查询候选表的字段结构和示例数据（小样本）以确认字段语义。
4. 再做术语归一化（例如 `预算 -> Budget1`，`分摊给 -> Allocation 场景`）。
5. 按模板生成单条 SQL（允许 CTE，不允许多语句）。
6. 执行前必须通过 `sql_query.py` 内置校验。
7. 只允许用 `scripts/sql_query.py` 执行 SQL，获取结果后再输出分析结论。
8. 每完成一个关键步骤后更新 `todo` 状态，回答前确保最后一项为 `completed`。

## 文档与脚本分工

- `references/metadata.md`
  - 业务表清单、意图到表映射、关键词到表映射。
- `references/schema_query_guide.md`
  - 查询数据结构时应使用的系统表 SQL（如 `INFORMATION_SCHEMA.COLUMNS`）。
- `references/sql_templates.md`
  - 常用查询模板（汇总、对比、分摊、趋势）与参数说明。
- `references/react_rules.md`
  - 业务硬约束与口径规则。
- `references/react_constraints.md`
  - 术语、字段值、联表限制。
- `references/workflow.md`
  - 执行顺序与失败回退策略。
- `references/module_map.md`
  - 当前技能目录结构与职责边界。
- `scripts/sql_query.py`
  - 唯一 SQL 执行入口，含 SQL 合法性校验和结构化错误返回。

## 查询数据结构时的引用规范

- 优先引用：`references/metadata.md`
- 需要字段级结构时：`references/schema_query_guide.md`
- 需要确认字段取值形态时：先执行样例数据查询（见 `references/schema_query_guide.md`）
- 结构探测 SQL 的执行脚本：`scripts/sql_query.py`

## 执行约束

- 不使用 `python -c`。
- 不调用已废弃脚本（例如 `run_query.py`、`generate_alloc_sql.py` 等）。
- 仅使用：
  - `python skills/finance/scripts/sql_query.py --sql "SELECT 1"`

## Todo 命中率优化规则

- 下列场景必须调用 `todo`：
  - 需要读取 2 个及以上参考文档；
  - 需要先查结构再写业务 SQL；
  - 包含“对比/趋势/分摊”且需要两段以上推理。
- 最小任务模版：
  - `in_progress`: 解析问题与约束
  - `pending`: 生成并校验 SQL
  - `pending`: 执行并解释结果
- 当收到系统提醒 `<reminder>Update your todos.</reminder>` 时，必须立即调用 `todo` 更新，不可跳过。

## SQL 生成约束

- 只生成单条语句，允许 `WITH ... SELECT`。
- 必须是查询语句：以 `SELECT` 或 `WITH` 开头，且必须包含 `SELECT` 子句。
- 禁止 DDL/DML（`DROP`、`DELETE`、`UPDATE`、`INSERT`、`ALTER`、`CREATE`、`TRUNCATE`、`EXEC`）。
- 禁止事务与过程控制语句（`BEGIN`、`COMMIT`、`ROLLBACK`、`SAVEPOINT`、`CALL`、`DO`、`COPY`）。
- 禁止 `SELECT INTO`（查询模式不允许创建对象）。
- 执行后必须返回结果集；不返回结果集的语句会被拒绝。
- 对比类问题必须输出可计算差值与变化率的字段。
- 分摊类问题必须体现 `Amount * normalized_rate` 口径，不能直接用 `SUM(Amount)` 代替分摊金额。

## 最终 SQL 思维链路（必须按序执行）

1. 问题定类

- 先判断是汇总、对比、趋势还是分摊。
- 命中 `分摊/allocation/allocated to` 时，直接走分摊链路，不可退化为普通汇总。

2. 口径定锚

- 先定 `Year`、`Scenario`、`Function`、`Key`。
- Scenario 必须先归一化（`Budget/BGT -> Budget1`，`Actual -> Actual`）。
- 分摊题必须先绑定 `Function + Key`：
  - `IT Allocation -> 480056 Cycle`
  - `HR Allocation -> 480055 Cycle`

3. 维度定锚

- 必须确定分摊主体是 `CC` 还是 `BL`。
- 未确定前禁止生成最终 SQL；先做结构/样例探测。

4. 粒度定锚

- 分摊计算粒度是“月度成本 x 月度比例”，再做汇总。
- 禁止先按年汇总成本后再乘比例。

5. 联接定锚

- 分摊联接必须满足四重关联：`Year + Scenario + Key + Month`。
- 若 `Rate` 存在重复粒度，必须先归一化/去重再联接，防止金额放大。

6. 结果定锚

- 最终 SQL 必须是单语句、可执行、返回结果集。
- 若与业务预期偏差显著，优先回查“主体过滤是否缺失、联接是否放大、年份口径是否错误”。

### 分摊 SQL 有效性硬门槛（未满足即判无效并重生成）

- 分摊题必须满足四重关联：
  - `c.[Year] = r.[Year]`
  - `c.[Scenario] = r.[Scenario]`
  - `c.[Key] = r.[Key]`
  - `c.[Month] = r.[Month]`
- 分摊题必须同时满足 `Function + Key` 绑定：
  - `IT Allocation` -> `480056 Cycle`
  - `HR Allocation` -> `480055 Cycle`
- 任一条件缺失即视为无效 SQL，必须重生成，禁止继续执行。

## 校验失败返回格式

- `scripts/sql_query.py` 在校验失败时返回结构化 JSON：
  - `ok`: `false`
  - `stage`: `validation`
  - `error.code`: 如 `SQL_VALIDATION_FAILED`、`QUERY_ONLY_ENFORCED`
  - `error.reasons`: 具体失败原因列表（例如 `MULTI_STATEMENT`、`SELECT_INTO_NOT_ALLOWED`）
- 生成端应根据 `error.reasons` 重写 SQL 后再执行。
