# 示例库与使用示例

## 三、内置问题 - SQL 示例库（精准匹配需求生成，风格 / 逻辑统一）

**Q2：FY26 计划了多少 HR 费用预算？（明细查询 + 单独聚合汇总）**

需求特征：筛选指定 Year/Scenario/Function，先查明细，再单独聚合总金额；聚合用 SUM (CAST ([Amount] AS FLOAT))。

统一示例：scripts/example_overview.py（Python 生成 → 执行 SQL）

### 3.2 复杂分摊计算类（跨表关联）

**Q3：FY25 实际分摊给 CT 的 IT 费用是多少？（双表联查 + BL 维度分摊 + 聚合）**

需求特征：主表 + 规则表四重关联，按 BL 字段筛选分摊主体，核心计算：基础金额 × 分摊比例，按维度分组聚合。

说明：分摊模板的具体 SQL 已由脚本维护为 `ALLOC_TEMPLATE` 字符串，不再在文档中直接输出复杂 SQL。请在 Python 中调用 `generate_alloc_sql(...)` 以获得单条 CTE SQL，并执行 SQL 后在 Python 中做汇总/对比分析。

统一示例：scripts/example_overview.py

**Q4：分摊给 413001 的 HR 费用变化 (FY26 BGT vs FY25 Actual)（双表联查 + CC 维度 + 跨周期对比 + UNION ALL）**

需求特征：双表联查 + CC 字段优先筛选，跨 Year/Scenario 对比，UNION ALL 合并结果，按月排序。

说明：Q4 的复杂 SQL 已改造成调用 `generate_alloc_sql()` 的流程，建议系统执行步骤如下：

1. 在 Python 中调用 `generate_alloc_sql(years=['FY26','FY25'], scenarios=['Budget1','Actual'], function_name='HR Allocation', party_field='t7.[CC]', party_value="'413001'")` 生成 SQL 字符串。
2. 使用 SQL 执行工具执行生成的 SQL 并返回年度分摊与同比对比结果。
3. 在 Python 中对结果做进一步分析或直接输出自然语言结论：
   - 提取各年的年度分摊金额（Year_Allocated_Cost）；
   - 查看同比差值与变动率（Allocated_Cost_Diff、Allocated_Cost_Diff_Rate(%)）。
   - 差值 > 0 表示增加，差值 < 0 表示减少。
4. 将分析结果以自然语言回答给用户（示例："FY26 分摊给 413001 的年度分摊金额为 X，较 FY25 增长 Y，增幅 Z%"）。

统一示例：scripts/example_overview.py

### 3.3 同比 / 环比分析与趋势类（CTE 实现 + 变化率 / 环比计算）

**Q5：采购费用从 FY25 Actual 到 FY26 BGT 的变化？（CTE + 跨周期对比 + 变化额 / 变化率计算）**

需求特征：单条 SQL 实现，CTE 分步计算基础数据、提取对比值、计算变化额 / 变化率，UNION ALL 合并结果，排序键控制展示顺序；变化率含除零保护，保留 2 位小数。

统一示例：scripts/example_overview.py（Python 生成 → 执行 SQL → Python 分析）

**Q6：HR 费用的月度趋势如何？（CTE + 月度汇总 + 环比增长率计算）**

需求特征：CTE 生成月度基础数据（含 month_num 数字排序），自关联实现环比计算，环比增长率含除零 / 空值保护，保留 2 位小数，按 month_num 升序排序。

统一示例：scripts/example_overview.py（Python 生成 → 执行 SQL → Python 分析）

**Q7：26 财年预算分摊给 413001 的 HR 费用和 25 财年实际分摊给 XP 的 HR 费用对比变化（跨维度跨周期对比）**

需求特征：双表联查，不同周期（FY26 Budget1/FY25 Actual）+ 不同分摊维度（CC/BL）对比，参考 Q4/Q5 逻辑，合并分摊计算 + 变化率计算。

核心逻辑：CC 号 413001、BL 值 XP 分别作为不同周期的筛选条件，这两个赛选字段有优先级，元数据中 BL 与 CC 是一对多关系，如果 CC 号包含在 BL 的取值范围中则以 CC 号作为筛选字段。在当前场景下已知 413001 属于 XP 因此以 CC 号作为筛选条件。双表四重关联，计算各周期分摊金额后对比变化额 / 变化率。

统一示例：scripts/example_overview.py（Python 生成 → 执行 SQL → Python 对比分析）

```

```
