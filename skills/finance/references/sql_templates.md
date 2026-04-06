# SQL 模板参考

本文档提供各类财务查询的标准SQL模板。

## 表别名规范

- 主表: `cdb` = `cost_database`
- 规则表: `t7` = `rate_table`

**注意**: 使用双引号 `"FieldName"` (PostgreSQL)，不是方括号 `[FieldName]` (SQL Server)

## 模板 1: 普通费用汇总

```sql
SELECT
    year,
    scenario,
    SUM(CAST(amount AS FLOAT)) as total_amount
FROM cost_database
WHERE function = '{function}'
    AND scenario IN ('Budget1', 'Actual')
    AND year IN ('FY25', 'FY26')
GROUP BY year, scenario
ORDER BY year, scenario;
```

## 模板 2: IT Allocation 分摊到指定 CC

```sql
SELECT
    cdb.year,
    cdb.scenario,
    SUM(CAST(cdb.amount AS FLOAT) * CAST(t7.rate_no AS NUMERIC)) as total_allocated_amount
FROM "cost_database" cdb
JOIN "rate_table" t7
    ON cdb.year = t7.year
    AND cdb.scenario = t7.scenario
    AND cdb.month = t7.month
    AND cdb.key = t7.key
WHERE cdb.function = 'IT Allocation'
    AND cdb.account = '{it_account}'
    AND t7.cc = '{target_cc}'
    AND t7.key = '{it_cycle_key}'
    AND cdb.scenario IN ('Budget1', 'Actual')
    AND cdb.year IN ('FY25', 'FY26')
GROUP BY cdb.year, cdb.scenario
ORDER BY cdb.year, cdb.scenario;
```

## 模板 3: IT Allocation 分摊到指定 BL

```sql
SELECT
    cdb.year,
    cdb.scenario,
    SUM(CAST(cdb.amount AS FLOAT) * CAST(t7.rate_no AS NUMERIC)) as total_allocated_amount
FROM "cost_database" cdb
JOIN "rate_table" t7
    ON cdb.year = t7.year
    AND cdb.scenario = t7.scenario
    AND cdb.month = t7.month
    AND cdb.key = t7.key
WHERE cdb.function = 'IT Allocation'
    AND cdb.account = '{it_account}'
    AND t7.bl = '{target_bl}'
    AND t7.key = '{it_cycle_key}'
    AND cdb.scenario IN ('Budget1', 'Actual')
    AND cdb.year IN ('FY25', 'FY26')
GROUP BY cdb.year, cdb.scenario
ORDER BY cdb.year, cdb.scenario;
```

## 模板 4: HR Allocation 分摊到指定 CC

```sql
SELECT
    cdb.year,
    cdb.scenario,
    SUM(CAST(cdb.amount AS FLOAT) * CAST(t7.rate_no AS NUMERIC)) as total_allocated_amount
FROM "cost_database" cdb
JOIN "rate_table" t7
    ON cdb.year = t7.year
    AND cdb.scenario = t7.scenario
    AND cdb.month = t7.month
    AND cdb.key = t7.key
WHERE cdb.function = 'HR Allocation'
    AND cdb.account = '{hr_account}'
    AND t7.cc = '{target_cc}'
    AND t7.key = '{hr_cycle_key}'
    AND cdb.scenario IN ('Budget1', 'Actual')
    AND cdb.year IN ('FY25', 'FY26')
GROUP BY cdb.year, cdb.scenario
ORDER BY cdb.year, cdb.scenario;
```

## 模板 5: HR Allocation 分摊到指定 BL

```sql
SELECT
    cdb.year,
    cdb.scenario,
    SUM(CAST(cdb.amount AS FLOAT) * CAST(t7.rate_no AS NUMERIC)) as total_allocated_amount
FROM "cost_database" cdb
JOIN "rate_table" t7
    ON cdb.year = t7.year
    AND cdb.scenario = t7.scenario
    AND cdb.month = t7.month
    AND cdb.key = t7.key
WHERE cdb.function = 'HR Allocation'
    AND cdb.account = '{hr_account}'
    AND t7.bl = '{target_bl}'
    AND t7.key = '{hr_cycle_key}'
    AND cdb.scenario IN ('Budget1', 'Actual')
    AND cdb.year IN ('FY25', 'FY26')
GROUP BY cdb.year, cdb.scenario
ORDER BY cdb.year, cdb.scenario;
```

## 模板 6: 多Scenario对比分析

```sql
WITH allocation_data AS (
    SELECT
        cdb.year,
        cdb.scenario,
        SUM(CAST(cdb.amount AS FLOAT) * CAST(t7.rate_no AS NUMERIC)) as allocated_amount
    FROM "cost_database" cdb
    JOIN "rate_table" t7
        ON cdb.year = t7.year
        AND cdb.scenario = t7.scenario
        AND cdb.month = t7.month
        AND cdb.key = t7.key
    WHERE cdb.function = '{allocation_function}'
        AND t7."{target_dim}" = '{target_value}'
        AND t7.key = '{cycle_key}'
        AND cdb.year = '{year}'
    GROUP BY cdb.year, cdb.scenario
)
SELECT
    year,
    scenario,
    allocated_amount,
    LAG(allocated_amount) OVER (ORDER BY scenario) as prev_amount,
    CASE
        WHEN LAG(allocated_amount) OVER (ORDER BY scenario) != 0
        THEN (allocated_amount - LAG(allocated_amount) OVER (ORDER BY scenario))
             / LAG(allocated_amount) OVER (ORDER BY scenario) * 100
        ELSE 0
    END as change_pct
FROM allocation_data;
```

## 模板 7: 按月趋势分析

```sql
SELECT
    cdb.year,
    cdb.scenario,
    cdb.month,
    SUM(CAST(cdb.amount AS FLOAT) * CAST(t7.rate_no AS NUMERIC)) as monthly_amount
FROM "cost_database" cdb
JOIN "rate_table" t7
    ON cdb.year = t7.year
    AND cdb.scenario = t7.scenario
    AND cdb.month = t7.month
    AND cdb.key = t7.key
WHERE cdb.function = '{allocation_function}'
    AND t7."{target_dim}" = '{target_value}'
    AND t7.key = '{cycle_key}'
    AND cdb.year = '{year}'
    AND cdb.scenario = '{scenario}'
GROUP BY cdb.year, cdb.scenario, cdb.month
ORDER BY cdb.month::INTEGER;
```

## 关键参数说明

| 参数 | 说明 | 获取方式 |
|-----|------|---------|
| `{it_account}` | IT分摊账户 | 查询 `"cost_database"` 表 `account` 字段 |
| `{hr_account}` | HR分摊账户 | 查询 `"cost_database"` 表 `account` 字段 |
| `{it_cycle_key}` | IT分摊Key | 查询 `"rate_table"` 表 `key` 字段 |
| `{hr_cycle_key}` | HR分摊Key | 查询 `"rate_table"` 表 `key` 字段 |
| `{target_cc}` | 目标成本中心 | 用户指定 |
| `{target_bl}` | 目标业务线 | 用户指定 |
| `{target_dim}` | 目标维度 | `bl` 或 `cc` |

## PostgreSQL 语法提醒

- ✅ 使用双引号: `"FieldName"`
- ❌ 不要使用方括号: `[FieldName]`
- ✅ 使用 `LIMIT n`
- ❌ 不要使用 `TOP n`
