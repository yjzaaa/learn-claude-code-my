---
name: finance
description: 回答财务数据分析问题，包括费用查询、IT/HR分摊计算、预算实际对比分析、趋势分析等。当用户询问费用、分摊、预算、实际、对比等财务相关问题时触发。
---

# Finance 技能

回答 SSME_FI_InsightBot 数据库的财务数据分析问题（表名：cost_database, rate_table）。

## ⚠️ 强制指令：禁止探索数据库结构

**执行任何查询前，先完整阅读本 SKILL.md 内容。**

**【绝对禁止】以下行为会浪费 token 和时间：**
- ❌ 禁止执行 `SELECT * FROM information_schema.columns`
- ❌ 禁止执行 `SELECT * FROM information_schema.tables`
- ❌ 禁止执行 `SELECT DISTINCT ... FROM ...` 来查枚举值
- ❌ 禁止先查 "有哪些表" 再查 "表结构" 再查 "示例数据"

**【为什么禁止】**
下方已提供完整的表结构、字段说明和枚举值。任何探索性查询都是冗余的，会：
1. 浪费 API 调用和 token
2. 延长响应时间
3. 可能导致错误（如使用 SQLite 语法查询 PostgreSQL）

**【正确做法】**
直接使用下方【核心表结构】和【固定数据结构字典】中的信息生成 SQL。

---

## 问题类型快速判断

| 关键词 | 类型 | 操作 |
|-------|------|------|
| "分摊给/至/到", "allocated to" | **分摊题** | 使用【分摊题 SQL 模板】 |
| "对比", "vs", "差异" | 对比分析 | 使用 CTE + LAG 函数 |
| "趋势", "变化", "增长" | 趋势分析 | 使用 CTE + 自关联 |
| "费用", amount | 普通查询 | 单表 SUM 聚合 |

---

## 核心表结构（已提供，禁止查询）

### 主表：cost_database

| 字段名 | 类型 | 说明 | 示例值 |
|-------|------|------|--------|
| id | INTEGER | 主键ID | 1 |
| year | VARCHAR | 财年 | 'FY25', 'FY26' |
| scenario | VARCHAR | 场景 | 'Actual', 'Budget1' |
| month | VARCHAR | 月份 | 'Oct', 'Nov', 'Dec'等 |
| function | VARCHAR | 功能类型 | 'IT Allocation', 'HR Allocation', 'IT', 'HR', 'G&A' |
| cost_text | VARCHAR | 成本描述 | 'HR', 'IT服务'等 |
| account | VARCHAR | 账户代码 | '91800160.0' |
| category | VARCHAR | 成本分类 | 'Functional cost', 'Cost center cost' |
| key | VARCHAR | 分摊Key | '480055 Cycle', '480056 Cycle', 'headcount'等 |
| year_total | VARCHAR | 年度总金额 | '9858298.13' |
| amount | VARCHAR | 金额（月度） | '-12345.67' |
| created_at | TIMESTAMP | 创建时间 | '2026-02-01 01:13:42.928569' |

### 规则表：rate_table

| 字段名 | 类型 | 说明 | 示例值 |
|-------|------|------|--------|
| id | INTEGER | 主键ID | 72577 |
| bl | VARCHAR | 业务线 | 'CT', 'XP', 'CS_DX', 'MP'等 |
| cc | VARCHAR | 成本中心 | '413001', '470072', '415012'等 |
| year | VARCHAR | 财年 | 'FY25', 'FY26' |
| scenario | VARCHAR | 场景 | 'Actual', 'Budget1' |
| month | VARCHAR | 月份 | 'Oct', 'Nov', 'Dec'等 |
| key | VARCHAR | 分摊Key | '480055 Cycle', '480056 Cycle', 'Pooling'等 |
| rate_no | VARCHAR | 分摊率（小数） | '0.020800' = 2.08% |
| created_at | TIMESTAMP | 创建时间 | '2026-02-01 01:13:44.107718' |

---

## 固定数据结构字典（直接使用）

### Year 有效值
- 'FY25', 'FY26', 'FY24'

### Scenario 有效值及同义词映射
| SQL值 | 同义词 |
|-------|--------|
| 'Actual' | 实际、Actual、本年、Act |
| 'Budget1' | BGT、Budget、预算、计划、BGT1 |

### Function 有效值
| 值 | 使用场景 |
|----|----------|
| 'IT Allocation' | **分摊题必须使用** |
| 'HR Allocation' | **分摊题必须使用** |
| 'IT' | 普通IT费用（非分摊） |
| 'HR' | 普通HR费用（非分摊） |
| 'G&A' | 管理费用 |

### Allocation Key 固定映射（分摊题必填）
- IT Allocation → Key = '480056 Cycle'
- HR Allocation → Key = '480055 Cycle'

---

## 标准工作流程

### 步骤 1: 解析参数（10秒内）

从用户问题中提取：
```
年份: FY25 / FY26
场景: Actual / Budget1
类型: 分摊题 / 普通查询
维度: CC (成本中心) / BL (业务线)
目标值: 如 'CT'
Function: IT Allocation / HR Allocation / IT / HR
```

### 步骤 2: 选择 SQL 模板（10秒内）

**分摊题模板:**
```sql
SELECT
    SUM(CAST(cdb.amount AS FLOAT) * CAST(t7.rate_no AS NUMERIC)) as allocated_amount
FROM cost_database cdb
JOIN rate_table t7
    ON cdb.year = t7.year
    AND cdb.scenario = t7.scenario
    AND cdb.month = t7.month
    AND cdb.key = t7.key
WHERE cdb.function = 'IT Allocation'  -- 或 'HR Allocation'
    AND cdb.key = '480056 Cycle'      -- IT用480056, HR用480055
    AND t7.bl = 'CT'                   -- 或 t7.cc = '413001'
    AND cdb.year = 'FY25'
    AND cdb.scenario = 'Actual'
```

**普通费用查询模板:**
```sql
SELECT
    SUM(CAST(amount AS FLOAT)) as total_amount
FROM cost_database
WHERE function = 'IT'
    AND year = 'FY25'
    AND scenario = 'Actual'
```

### 步骤 3: 执行并解释（30秒内）

1. 执行 SQL
2. 解释结果（负数=分摊出去，正数=分摊进来）

---

## 强制规则

### 表名（必须正确）
- ✅ `cost_database`
- ✅ `rate_table`
- ❌ `cost_allocation` (数据库名)
- ❌ `"SSME_FI_InsightBot_CostDataBase"` (旧表名，不再使用)

### 字段名（PostgreSQL语法）
- ✅ `function`, `year`, `amount`
- ❌ `[Function]` (SQL Server语法)

### Allocation 强制规则
- IT分摊: `function = 'IT Allocation'` + `key = '480056 Cycle'`
- HR分摊: `function = 'HR Allocation'` + `key = '480055 Cycle'`
- **分摊题禁止**: 使用 `'IT'` 或 `'HR'`

### rate_no 计算规则
- ✅ `CAST(rate_no AS NUMERIC)` 直接转换
- ❌ `CAST(rate_no AS NUMERIC) / 100` (多除100倍)

---

## 示例：25财年实际分摊给CT的IT费用

**解析参数:**
- 年份: FY25
- 场景: Actual
- 类型: 分摊题
- Function: IT Allocation
- Key: 480056 Cycle
- 维度: BL = 'CT'

**直接执行SQL:**
```sql
SELECT
    SUM(CAST(cdb.amount AS FLOAT) * CAST(t7.rate_no AS NUMERIC)) as allocated_amount
FROM cost_database cdb
JOIN rate_table t7
    ON cdb.year = t7.year
    AND cdb.scenario = t7.scenario
    AND cdb.month = t7.month
    AND cdb.key = t7.key
WHERE cdb.function = 'IT Allocation'
    AND cdb.key = '480056 Cycle'
    AND t7.bl = 'CT'
    AND cdb.year = 'FY25'
    AND cdb.scenario = 'Actual';
```

**解释:** 结果为负表示分摊出去的费用，为正表示分摊进来的费用。

---

## 参考文件（按需读取）

- `references/react_constraints.md` - 复杂分摊逻辑细节
- `references/react_examples.md` - 对比/趋势分析示例
- `references/sql_templates.md` - 更多SQL模板
