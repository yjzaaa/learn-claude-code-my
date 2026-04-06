# 数据库表结构查询指南

本文档提供标准的数据库表结构查询流程，用于快速了解表结构和示例数据。

## 标准查询流程

### 步骤 1: 查询所有表名

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
    AND table_name LIKE '%insight%'
ORDER BY table_name;
```

### 步骤 2: 查询目标表的结构

以 `cost_database` 为例：

```sql
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'cost_database'
ORDER BY ordinal_position;
```

### 步骤 3: 查询示例数据（前5行）

```sql
SELECT *
FROM "cost_database"
LIMIT 5;
```

### 步骤 4: 查询枚举值（关键字段）

```sql
-- 查询所有 Function 类型
SELECT DISTINCT function
FROM "cost_database"
ORDER BY function;

-- 查询所有 Year
SELECT DISTINCT year
FROM "cost_database"
ORDER BY year;

-- 查询所有 Scenario
SELECT DISTINCT scenario
FROM "cost_database"
ORDER BY scenario;
```

## 核心表结构

### cost_database (费用数据主表)

| 字段名 | 类型 | 说明 |
|-------|------|------|
| Year | VARCHAR | 财年 (FY25, FY26) |
| Scenario | VARCHAR | 场景 (Actual, Budget1) |
| Month | VARCHAR | 月份 (1-12) |
| Function | VARCHAR | 功能类型 (IT Allocation, HR Allocation, IT, HR, G&A 等) |
| Account | VARCHAR | 账户代码 |
| Key | VARCHAR | 分摊周期 Key (如 480055 Cycle, 480056 Cycle) |
| Amount | FLOAT | 金额 |

### rate_table (分摊率表)

| 字段名 | 类型 | 说明 |
|-------|------|------|
| Year | VARCHAR | 财年 |
| Scenario | VARCHAR | 场景 |
| Month | VARCHAR | 月份 |
| Key | VARCHAR | 分摊周期 Key |
| CC | VARCHAR | 成本中心 (6位) |
| BL | VARCHAR | 业务线 |
| RateNo | VARCHAR | 分摊率 (小数形式，如 0.020800 = 2.08%) |

## 快速查询模板

### 一键查询表结构和示例数据

```sql
-- 查询表结构
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'cost_database'
ORDER BY ordinal_position;

-- 查询示例数据（PostgreSQL 语法）
SELECT *
FROM "cost_database"
LIMIT 3;

-- 查询 Function 枚举值
SELECT DISTINCT function
FROM "cost_database";
```

## 注意事项

1. **表名大小写**: PostgreSQL 中表名默认小写，但原表使用驼峰命名，查询时需要加双引号 `"cost_database"`
2. **字段名**: 字段名需要使用双引号 `function`、`year`、`scenario` 等
3. **RateNo 格式**: 存储为小数字符串，直接使用 CAST(rate_no AS NUMERIC)，无需除以 100
4. **LIMIT vs TOP**: PostgreSQL 使用 `LIMIT n`，不是 SQL Server 的 `TOP n`
5. **方括号**: 不要使用 SQL Server 的方括号 `[Field]`，使用双引号 `"Field"`
