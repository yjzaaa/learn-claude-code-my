# 示例库与模板映射

本文件用于把常见业务问题映射到 `sql_templates.md` 中的模板。

## Q1 预算汇总

- 问题类型：某年某场景某职能费用汇总
- 使用模板：`TEMPLATE_SUMMARY_BY_FILTERS`

## Q2 预算 vs 实际对比

- 问题类型：两个周期金额差异与变化率
- 使用模板：`TEMPLATE_VARIANCE_BETWEEN_PERIODS`

## Q3 分摊金额

- 问题类型：按 BL 或 CC 计算分摊金额
- 使用模板：`TEMPLATE_ALLOCATION_COST`

### 分摊场景识别示例（避免漏判）

- 示例 1：`FY25 实际分摊给 CT 的 IT 费用是多少？`
  - 识别：分摊场景
  - Function：`IT Allocation`
  - 维度：`r.[BL] = 'CT'`
  - 关联表：`CostDataBase + Rate`

- 示例 2：`FY26 预算分摊给 413001 的 HR 费用是多少？`
  - 识别：分摊场景
  - Function：`HR Allocation`
  - 维度：`r.[CC] = '413001'`
  - 关联表：`CostDataBase + Rate`

- 示例 3：`比较 FY26 BGT 分摊给 413001 与 FY25 Actual 分摊给 XP 的 HR 费用`
  - 识别：分摊 + 跨周期对比
  - 模板组合：`TEMPLATE_ALLOCATION_COST` + `TEMPLATE_VARIANCE_BETWEEN_PERIODS`
  - 若 CC/BL 归属冲突：增加 `CCMapping` 探测与映射

### 触发关键词（命中任一即优先按分摊处理）

- `分摊`
- `allocation`
- `allocated to`
- `按比例`
- `分摊给`
- `rate`

### 反例与正例（防止生成劣质 SQL）

- 反例：只按 `Month` 联 `Rate`，且没有 `Key` 约束。
- 正例：必须使用四重关联
  - `c.[Year] = r.[Year]`
  - `c.[Scenario] = r.[Scenario]`
  - `c.[Key] = r.[Key]`
  - `c.[Month] = r.[Month]`

- 反例：`c.[Function] = 'IT Allocation'` 但不限制 `c.[Key]`。
- 正例：`IT Allocation` 同时要求 `c.[Key] = '480056 Cycle'`；`HR Allocation` 同时要求 `c.[Key] = '480055 Cycle'`。

- 反例：年份直接写 `2025`（若库内是 `FY25`）。
- 正例：先探测 Year/Scenario 枚举值，再填入模板参数。

## Q4 月度趋势

- 问题类型：按月输出金额和环比
- 使用模板：`TEMPLATE_MONTHLY_TREND`

## 统一执行方式

- SQL 生成后，必须使用 `scripts/sql_query.py` 执行。
- 若执行脚本返回结构化校验错误，先修复 SQL 再执行。
