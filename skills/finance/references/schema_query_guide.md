# 数据结构查询指南

本文件说明在生成业务 SQL 前，如何查询表结构和示例数据。

## 何时查询结构

- 用户问题涉及未知字段。
- 需要确认字段类型、可空性、默认值。
- 执行报错提示字段不存在。

## 何时查询示例数据

- 需要确认字段真实取值（例如 `Scenario` 的枚举值）。
- 需要验证过滤条件是否有数据命中。
- 字段语义在文档中不够明确。

## 推荐顺序

1. 先看 `metadata.md` 确认候选业务表。
2. 用下面模板查询结构。
3. 用示例数据模板查询小样本（每表 5-10 行）。
4. 通过 `scripts/sql_query.py` 执行上述查询 SQL。

## SQL Server 字段结构查询模板

```sql
SELECT
    TABLE_SCHEMA,
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME IN (
    'SSME_FI_InsightBot_CostDataBase',
    'SSME_FI_InsightBot_Rate',
    'SSME_FI_InsightBot_CCMapping'
)
ORDER BY TABLE_NAME, ORDINAL_POSITION;
```

## 单表快速查询

```sql
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dbo'
  AND TABLE_NAME = 'SSME_FI_InsightBot_CostDataBase'
ORDER BY ORDINAL_POSITION;
```

## 示例数据查询模板

```sql
SELECT TOP 10
    *
FROM dbo.SSME_FI_InsightBot_CostDataBase;
```

```sql
SELECT TOP 10
    *
FROM dbo.SSME_FI_InsightBot_Rate;
```

```sql
SELECT TOP 10
    *
FROM dbo.SSME_FI_InsightBot_CCMapping;
```

## 枚举值快速探测模板

```sql
SELECT DISTINCT TOP 20 [Scenario]
FROM dbo.SSME_FI_InsightBot_CostDataBase
ORDER BY [Scenario];
```

```sql
SELECT DISTINCT TOP 20 [Function]
FROM dbo.SSME_FI_InsightBot_CostDataBase
ORDER BY [Function];
```

## 约束

- 结构查询也必须是单条 SQL。
- 示例数据查询必须限制返回行数（建议 TOP 5/10/20）。
- 禁止执行任何 DDL/DML。
- 结构查询结果只用于字段确认，不直接当业务答案。
- 示例数据结果只用于语义校验与条件确认，不直接当业务结论。
