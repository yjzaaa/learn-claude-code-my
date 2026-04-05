# SQL 模板参考

本文档提供各类财务查询的标准SQL模板。

## 表别名规范

- 主表: `cdb` = `SSME_FI_InsightBot_CostDataBase`
- 规则表: `t7` = `SSME_FI_InsightBot_Rate`

## 模板 1: 普通费用汇总

```sql
SELECT 
    [Year],
    [Scenario],
    SUM(CAST([Amount] AS FLOAT)) as total_amount
FROM SSME_FI_InsightBot_CostDataBase
WHERE [Function] = '{function}'
    AND [Scenario] IN ('Budget1', 'Actual')
    AND [Year] IN ('FY25', 'FY26')
GROUP BY [Year], [Scenario]
ORDER BY [Year], [Scenario]
```

## 模板 2: IT Allocation 分摊到指定 CC

```sql
SELECT 
    cdb.[Year],
    cdb.[Scenario],
    SUM(CAST(cdb.[Amount] AS FLOAT) * CAST(t7.[RateNo] AS NUMERIC)) as total_allocated_amount
FROM SSME_FI_InsightBot_CostDataBase cdb
JOIN SSME_FI_InsightBot_Rate t7 
    ON cdb.[Year] = t7.[Year] 
    AND cdb.[Scenario] = t7.[Scenario]
    AND cdb.[Month] = t7.[Month]
    AND cdb.[Key] = t7.[Key]
WHERE cdb.[Function] = 'IT Allocation'
    AND cdb.[Account] = '{it_account}'
    AND t7.[CC] = '{target_cc}'
    AND t7.[Key] = '{it_cycle_key}'
    AND cdb.[Scenario] IN ('Budget1', 'Actual')
    AND cdb.[Year] IN ('FY25', 'FY26')
GROUP BY cdb.[Year], cdb.[Scenario]
ORDER BY cdb.[Year], cdb.[Scenario]
```

## 模板 3: IT Allocation 分摊到指定 BL

```sql
SELECT 
    cdb.[Year],
    cdb.[Scenario],
    SUM(CAST(cdb.[Amount] AS FLOAT) * CAST(t7.[RateNo] AS NUMERIC)) as total_allocated_amount
FROM SSME_FI_InsightBot_CostDataBase cdb
JOIN SSME_FI_InsightBot_Rate t7 
    ON cdb.[Year] = t7.[Year] 
    AND cdb.[Scenario] = t7.[Scenario]
    AND cdb.[Month] = t7.[Month]
    AND cdb.[Key] = t7.[Key]
WHERE cdb.[Function] = 'IT Allocation'
    AND cdb.[Account] = '{it_account}'
    AND t7.[BL] = '{target_bl}'
    AND t7.[Key] = '{it_cycle_key}'
    AND cdb.[Scenario] IN ('Budget1', 'Actual')
    AND cdb.[Year] IN ('FY25', 'FY26')
GROUP BY cdb.[Year], cdb.[Scenario]
ORDER BY cdb.[Year], cdb.[Scenario]
```

## 模板 4: HR Allocation 分摊到指定 CC

```sql
SELECT 
    cdb.[Year],
    cdb.[Scenario],
    SUM(CAST(cdb.[Amount] AS FLOAT) * CAST(t7.[RateNo] AS NUMERIC)) as total_allocated_amount
FROM SSME_FI_InsightBot_CostDataBase cdb
JOIN SSME_FI_InsightBot_Rate t7 
    ON cdb.[Year] = t7.[Year] 
    AND cdb.[Scenario] = t7.[Scenario]
    AND cdb.[Month] = t7.[Month]
    AND cdb.[Key] = t7.[Key]
WHERE cdb.[Function] = 'HR Allocation'
    AND cdb.[Account] = '{hr_account}'
    AND t7.[CC] = '{target_cc}'
    AND t7.[Key] = '{hr_cycle_key}'
    AND cdb.[Scenario] IN ('Budget1', 'Actual')
    AND cdb.[Year] IN ('FY25', 'FY26')
GROUP BY cdb.[Year], cdb.[Scenario]
ORDER BY cdb.[Year], cdb.[Scenario]
```

## 模板 5: HR Allocation 分摊到指定 BL

```sql
SELECT 
    cdb.[Year],
    cdb.[Scenario],
    SUM(CAST(cdb.[Amount] AS FLOAT) * CAST(t7.[RateNo] AS NUMERIC)) as total_allocated_amount
FROM SSME_FI_InsightBot_CostDataBase cdb
JOIN SSME_FI_InsightBot_Rate t7 
    ON cdb.[Year] = t7.[Year] 
    AND cdb.[Scenario] = t7.[Scenario]
    AND cdb.[Month] = t7.[Month]
    AND cdb.[Key] = t7.[Key]
WHERE cdb.[Function] = 'HR Allocation'
    AND cdb.[Account] = '{hr_account}'
    AND t7.[BL] = '{target_bl}'
    AND t7.[Key] = '{hr_cycle_key}'
    AND cdb.[Scenario] IN ('Budget1', 'Actual')
    AND cdb.[Year] IN ('FY25', 'FY26')
GROUP BY cdb.[Year], cdb.[Scenario]
ORDER BY cdb.[Year], cdb.[Scenario]
```

## 模板 6: 多Scenario对比分析

```sql
WITH allocation_data AS (
    SELECT 
        cdb.[Year],
        cdb.[Scenario],
        SUM(CAST(cdb.[Amount] AS FLOAT) * CAST(t7.[RateNo] AS NUMERIC)) as allocated_amount
    FROM SSME_FI_InsightBot_CostDataBase cdb
    JOIN SSME_FI_InsightBot_Rate t7 
        ON cdb.[Year] = t7.[Year] 
        AND cdb.[Scenario] = t7.[Scenario]
        AND cdb.[Month] = t7.[Month]
        AND cdb.[Key] = t7.[Key]
    WHERE cdb.[Function] = '{allocation_function}'
        AND t7.[{target_dim}] = '{target_value}'
        AND t7.[Key] = '{cycle_key}'
        AND cdb.[Year] = '{year}'
    GROUP BY cdb.[Year], cdb.[Scenario]
)
SELECT 
    [Year],
    [Scenario],
    allocated_amount,
    LAG(allocated_amount) OVER (ORDER BY [Scenario]) as prev_amount,
    CASE 
        WHEN LAG(allocated_amount) OVER (ORDER BY [Scenario]) != 0 
        THEN (allocated_amount - LAG(allocated_amount) OVER (ORDER BY [Scenario])) 
             / LAG(allocated_amount) OVER (ORDER BY [Scenario]) * 100
        ELSE 0 
    END as change_pct
FROM allocation_data
```

## 模板 7: 按月趋势分析

```sql
SELECT 
    cdb.[Year],
    cdb.[Scenario],
    cdb.[Month],
    SUM(CAST(cdb.[Amount] AS FLOAT) * CAST(t7.[RateNo] AS NUMERIC)) as monthly_amount
FROM SSME_FI_InsightBot_CostDataBase cdb
JOIN SSME_FI_InsightBot_Rate t7 
    ON cdb.[Year] = t7.[Year] 
    AND cdb.[Scenario] = t7.[Scenario]
    AND cdb.[Month] = t7.[Month]
    AND cdb.[Key] = t7.[Key]
WHERE cdb.[Function] = '{allocation_function}'
    AND t7.[{target_dim}] = '{target_value}'
    AND t7.[Key] = '{cycle_key}'
    AND cdb.[Year] = '{year}'
    AND cdb.[Scenario] = '{scenario}'
GROUP BY cdb.[Year], cdb.[Scenario], cdb.[Month]
ORDER BY cdb.[Month]
```

## 关键参数说明

| 参数 | 说明 | 获取方式 |
|-----|------|---------|
| `{it_account}` | IT分摊账户 | 查询 `cost_database` 表 `account` 字段 |
| `{hr_account}` | HR分摊账户 | 查询 `cost_database` 表 `account` 字段 |
| `{it_cycle_key}` | IT分摊Key | 查询 `rate` 表 `key` 字段 |
| `{hr_cycle_key}` | HR分摊Key | 查询 `rate` 表 `key` 字段 |
| `{target_cc}` | 目标成本中心 | 用户指定 |
| `{target_bl}` | 目标业务线 | 用户指定 |
| `{target_dim}` | 目标维度 | `BL` 或 `CC` |
