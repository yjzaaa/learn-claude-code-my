# SQL 模板库（finance）

说明：本文件集中维护 SQL 模板。模型应复制模板结构并替换参数，不应拼接危险语句。

## 生成最终 SQL 前的思维检查

- 是否先确定题型（分摊/对比/趋势/汇总）？
- 是否先确认 Year/Scenario 的真实取值，而不是猜测值？
- 分摊题是否已绑定 `allocation_function + allocation_key`？
- 分摊题是否已明确 `party_field + party_value`（CC/BL 必填）？
- 是否使用四重关联（Year/Scenario/Key/Month）？
- 是否考虑了 `Rate` 重复粒度并先做归一化/去重？
- 结果异常偏大时，优先检查“主体过滤缺失”与“联接放大”。

## 场景确认（Scenario）

- 默认无需额外配置，先使用以下归一化：
  - `预算`/`Budget`/`BGT`/`计划` -> `Budget1`
  - `实际`/`Actual`/`ACT` -> `Actual`
- 若用户给出的 Scenario 不在已知映射中，先探测再生成业务 SQL。

### TEMPLATE_PROBE_SCENARIO_VALUES

用途：探测数据库中可用的 Scenario 值范围。

```sql
SELECT DISTINCT TOP 20 [Scenario]
FROM dbo.SSME_FI_InsightBot_CostDataBase
ORDER BY [Scenario];
```

## 分摊计算涉及表规则

- `SSME_FI_InsightBot_CostDataBase`：分摊基础金额来源（必需）。
- `SSME_FI_InsightBot_Rate`：分摊比例 `RateNo` 和主体维度 `CC/BL`（必需）。
- `SSME_FI_InsightBot_CCMapping`：仅在需要做 CC 与 BL 归属映射、或用户描述与 `Rate` 表维度不一致时启用（可选）。

### TEMPLATE_PROBE_ALLOCATION_DIMENSION

用途：探测分摊维度是否优先用 CC 或 BL。

```sql
SELECT TOP 20
    [CC],
    [BL],
    [Key],
    [RateNo]
FROM dbo.SSME_FI_InsightBot_Rate
WHERE [CC] IS NOT NULL OR [BL] IS NOT NULL;
```

## TEMPLATE_SUMMARY_BY_FILTERS

用途：按 Year/Scenario/Function 聚合金额。

```sql
SELECT
    [Year],
    [Scenario],
    [Function],
    SUM(CAST([Amount] AS FLOAT)) AS total_amount
FROM dbo.SSME_FI_InsightBot_CostDataBase
WHERE [Year] = '{{year}}'
  AND [Scenario] = '{{scenario}}'
  AND [Function] = '{{function_name}}'
GROUP BY [Year], [Scenario], [Function];
```

## TEMPLATE_VARIANCE_BETWEEN_PERIODS

用途：对比两个周期并计算差值与变化率。

```sql
WITH period_cost AS (
    SELECT
        [Year],
        [Scenario],
        SUM(CAST([Amount] AS FLOAT)) AS total_amount
    FROM dbo.SSME_FI_InsightBot_CostDataBase
    WHERE [Function] = '{{function_name}}'
      AND (
        ([Year] = '{{year_new}}' AND [Scenario] = '{{scenario_new}}') OR
        ([Year] = '{{year_old}}' AND [Scenario] = '{{scenario_old}}')
      )
    GROUP BY [Year], [Scenario]
)
SELECT
    MAX(CASE WHEN [Year] = '{{year_new}}' AND [Scenario] = '{{scenario_new}}' THEN total_amount END) AS new_value,
    MAX(CASE WHEN [Year] = '{{year_old}}' AND [Scenario] = '{{scenario_old}}' THEN total_amount END) AS old_value,
    MAX(CASE WHEN [Year] = '{{year_new}}' AND [Scenario] = '{{scenario_new}}' THEN total_amount END)
      - MAX(CASE WHEN [Year] = '{{year_old}}' AND [Scenario] = '{{scenario_old}}' THEN total_amount END) AS delta_value,
    CASE
      WHEN MAX(CASE WHEN [Year] = '{{year_old}}' AND [Scenario] = '{{scenario_old}}' THEN total_amount END) = 0 THEN 0
      ELSE (
        MAX(CASE WHEN [Year] = '{{year_new}}' AND [Scenario] = '{{scenario_new}}' THEN total_amount END)
        - MAX(CASE WHEN [Year] = '{{year_old}}' AND [Scenario] = '{{scenario_old}}' THEN total_amount END)
      )
      / NULLIF(MAX(CASE WHEN [Year] = '{{year_old}}' AND [Scenario] = '{{scenario_old}}' THEN total_amount END), 0)
    END AS change_rate
FROM period_cost;
```

## TEMPLATE_ALLOCATION_COST

用途：按分摊比例计算分摊金额（BL/CC）。

```sql
WITH rate_normalized AS (
  SELECT
    r.[Year],
    r.[Scenario],
    r.[Month],
    r.[Key],
    r.[BL],
    r.[CC],
    CASE
      WHEN TRY_CAST(REPLACE(r.[RateNo], '%', '') AS FLOAT) IS NULL THEN NULL
      WHEN CHARINDEX('%', r.[RateNo]) > 0 THEN TRY_CAST(REPLACE(r.[RateNo], '%', '') AS FLOAT) / 100.0
      ELSE TRY_CAST(r.[RateNo] AS FLOAT)
    END AS normalized_rate
  FROM dbo.SSME_FI_InsightBot_Rate r
),
rate_dedup AS (
  SELECT
    [Year],
    [Scenario],
    [Month],
    [Key],
    [BL],
    [CC],
    MAX(normalized_rate) AS normalized_rate
  FROM rate_normalized
  GROUP BY [Year], [Scenario], [Month], [Key], [BL], [CC]
),
base_data AS (
    SELECT
        c.[Year],
        c.[Scenario],
        c.[Month],
        c.[Function],
        c.[Key],
        c.[Amount],
    rd.[BL],
    rd.[CC],
    rd.normalized_rate
    FROM dbo.SSME_FI_InsightBot_CostDataBase c
  JOIN rate_dedup rd
    ON c.[Year] = rd.[Year]
   AND c.[Scenario] = rd.[Scenario]
   AND c.[Key] = rd.[Key]
   AND c.[Month] = rd.[Month]
    WHERE c.[Year] = '{{year}}'
      AND c.[Scenario] = '{{scenario}}'
      AND c.[Function] = '{{allocation_function}}'
      AND c.[Key] = '{{allocation_key}}'
      AND {{party_field}} = '{{party_value}}'
)
SELECT
    [Year],
    [Scenario],
    COALESCE(SUM(CAST([Amount] AS FLOAT) * COALESCE(normalized_rate, 0)), 0) AS allocated_amount
FROM base_data
GROUP BY [Year], [Scenario];
```

参数说明：

- `party_field` 只能取 `rd.[BL]` 或 `rd.[CC]`。
- `party_field`/`party_value` 在分摊题中是必填项，不可省略。
- `allocation_function` 只能取 `IT Allocation` 或 `HR Allocation`。
- `allocation_key` 必须和 `allocation_function` 对应：
  - `IT Allocation` -> `480056 Cycle`
  - `HR Allocation` -> `480055 Cycle`
- 若用户问题明确是“分摊给某 CC（如 413001）”，优先 `party_field = rd.[CC]`。
- 若用户问题是“分摊给某业务线（如 CT/XP）”，使用 `party_field = rd.[BL]`。

## 分摊场景常见错误（禁止写法）

- 仅按 `Month` 联表（会导致错配/重复计数）。
- 分摊题缺少 `Key` 过滤。
- 分摊题使用 `Function = 'IT'/'HR'` 而非 `IT Allocation`/`HR Allocation`。
- 年份值与库内口径不一致（例如数据库使用 `FY25`，却写成 `2025`）。

## TEMPLATE_MONTHLY_TREND

用途：按月输出金额与环比。

```sql
WITH monthly AS (
    SELECT
        [Year],
        [Scenario],
        [Month],
        SUM(CAST([Amount] AS FLOAT)) AS month_amount
    FROM dbo.SSME_FI_InsightBot_CostDataBase
    WHERE [Year] = '{{year}}'
      AND [Scenario] = '{{scenario}}'
      AND [Function] = '{{function_name}}'
    GROUP BY [Year], [Scenario], [Month]
), ranked AS (
    SELECT
        [Year],
        [Scenario],
        [Month],
        month_amount,
        LAG(month_amount) OVER (ORDER BY [Month]) AS prev_month_amount
    FROM monthly
)
SELECT
    [Year],
    [Scenario],
    [Month],
    month_amount,
    prev_month_amount,
    month_amount - COALESCE(prev_month_amount, 0) AS mom_delta,
    CASE
      WHEN COALESCE(prev_month_amount, 0) = 0 THEN 0
      ELSE (month_amount - prev_month_amount) / NULLIF(prev_month_amount, 0)
    END AS mom_rate
FROM ranked
ORDER BY [Month];
```
