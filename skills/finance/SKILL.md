---
name: finance
description: |
  财务成本分析技能。根据用户问题生成并执行 SQL 查询，返回基于数据的财务分析结论。
  支持：成本查询、分摊计算、预算对比、趋势分析。
---

# Finance Skill

## 核心能力

1. **成本查询** - 查询特定职能/业务线的成本数据
2. **分摊计算** - 计算成本分摊金额（按业务线/成本中心）
3. **预算对比** - 对比不同年份/版本的预算与实际
4. **趋势分析** - 分析成本变化趋势

## 数据模型

### 表结构

| 表名 | 用途 | 核心字段 |
|------|------|----------|
| `cost_database` | 存储成本数据 | `year`, `scenario`, `function`, `cost_text`, `key`, `month`, `amount`, `year_total` |
| `rate_table` | 存储分摊费率 | `year`, `scenario`, `month`, `key`, `bl`, `cc`, `rate_no` |
| `cc_mapping` | 成本中心映射 | `cost_center_number`, `business_line` |

### 关键字段值域

**Function (职能)**
- `IT`, `IT Allocation` - IT部门/IT分摊
- `HR`, `HR Allocation` - HR部门/HR分摊
- `Procurement` - 采购部门

**Scenario (版本)**
- `Actual` - 实际数
- `Budget1` - 预算
- `Rolling Forecast2` - 滚动预测

**Key (分摊标准)**
- `headcount` - 人头数
- `Win Acc` - Windows账号
- `WCW` - 白领
- `480055 Cycle` - HR分摊标识
- `480056 Cycle` - IT分摊标识

**BL (业务线)**
- `CT`, `XP`, `MP`, `MI`, `TI`, `DTI`, `UX` 等

## SQL 生成流程

```
用户问题
    ↓
[Step 1: 意图识别]
    - 识别查询类型（成本/分摊/对比/趋势）
    - 提取时间维度（FY25/FY26）
    - 提取版本维度（Actual/Budget1）
    - 提取职能维度（IT/HR/Procurement）
    ↓
[Step 2: 参数归一化]
    - "预算" → Budget1
    - "实际" → Actual
    - "分摊给CT" → bl='CT' 或 cc in (CT相关的CC)
    ↓
[Step 3: 查询表结构]
    - 查询目标表的字段结构，确认字段名和数据类型
    - SQL: SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'xxx'
    - 根据实际字段名调整SQL生成（避免使用错误的字段名）
    ↓
[Step 4: SQL模板选择]
    - 成本查询 → 直接查询 cost_database
    - 分摊计算 → JOIN cost_database + rate_table
    - 预算对比 → 分别查询两年数据后对比
    ↓
[Step 5: SQL生成与执行]
    ↓
结果分析与回答
```

## 查询模板

### 模板0: 表结构查询（SQL生成前必须先执行）

在生成业务SQL之前，必须先查询表的实际字段结构：

```sql
-- 查询表字段结构
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = '{table_name}'
  AND table_schema = 'public'
ORDER BY ordinal_position;
```

**使用方式**:
1. 先执行结构查询获取字段列表
2. 根据返回的字段名生成业务SQL
3. 避免因字段名错误导致SQL失败

**返回格式说明**:
```
column_name    | data_type       | is_nullable
---------------|-----------------|-------------
[字段名]       | [数据类型]      | YES/NO
```

### 模板1: 成本汇总查询

查询某职能的年度成本：

```sql
SELECT
    function,
    cost_text,
    key,
    SUM(amount) as total_amount
FROM cost_database
WHERE year = '{year}'
  AND scenario = '{scenario}'
  AND function = '{function}'
GROUP BY function, cost_text, key
ORDER BY total_amount DESC;
```

### 模板2: 分摊金额计算

计算分摊给特定业务线/成本中心的金额：

```sql
SELECT
    cdb.month,
    cdb.amount as base_cost,
    rt.rate_no,
    (cdb.amount * rt.rate_no / 100.0) as allocated_amount
FROM cost_database cdb
JOIN rate_table rt ON cdb.month = rt.month
    AND cdb.year = rt.year
    AND cdb.scenario = rt.scenario
    AND cdb.key = rt.key
WHERE cdb.year = '{year}'
  AND cdb.scenario = '{scenario}'
  AND cdb.function = '{allocation_function}'
  AND rt.{target_field} = '{target_value}'
ORDER BY cdb.month;
```

**分摊金额计算逻辑**:
- `Allocated Amount = base_cost * rate_no / 100`
- 负数表示成本分摊（费用）
- 需按年度汇总

### 模板3: 预算对比

对比两年数据：

```sql
-- 第一年数据
SELECT '{period_1_label}' as period, SUM(amount) as total
FROM cost_database
WHERE year = '{year_1}' AND scenario = '{scenario_1}' AND function = '{function}'

UNION ALL

-- 第二年数据
SELECT '{period_2_label}', SUM(amount)
FROM cost_database
WHERE year = '{year_2}' AND scenario = '{scenario_2}' AND function = '{function}';
```

**对比分析公式**:
- 变化值 = 新值 - 旧值
- 变化率 = (变化值 / 旧值) * 100

### 模板4: 成本中心列表查询

查询某业务线下的成本中心：

```sql
SELECT DISTINCT cc
FROM rate_table
WHERE bl = '{business_line}'
ORDER BY cc;
```

## 业务规则

### 规则1: 分摊题识别

当问题包含以下关键词时，按"分摊题"处理：
- "分摊给", "allocated to", "allocation to"
- "分摊给CT", "分摊给XP"

**分摊函数映射**:
- IT 分摊 → `function = 'IT Allocation'`, `key = '480056 Cycle'`
- HR 分摊 → `function = 'HR Allocation'`, `key = '480055 Cycle'`

### 规则2: 成本中心vs业务线

- 分摊给**业务线**（如CT）→ 使用 `rate_table.bl = 'CT'`
- 分摊给**成本中心**（如413001）→ 使用 `rate_table.cc = '413001'`

### 规则3: 对比分析输出

对比问题必须给出：
1. 绝对变化值（Delta = 新值 - 旧值）
2. 变化率（Change % = Delta / 旧值 * 100）
3. 结论说明（增长/下降及可能原因）

## 完整示例流程

### 示例: 查询"FY26 HR预算"

**完整执行流程**:

```
用户问题: "FY26 HR预算多少？"
    ↓
[Step 1: 意图识别]
    - 查询类型: 成本查询
    - 时间维度: FY26
    - 版本维度: Budget (需归一化为 Budget1)
    - 职能维度: HR
    - 目标表: cost_database
    ↓
[Step 2: 参数归一化]
    - "预算" → "Budget1"
    - "FY26" → "FY26"
    - "HR" → "HR"
    ↓
[Step 3: 查询表结构]
    SQL: SELECT column_name, data_type
         FROM information_schema.columns
         WHERE table_name = 'cost_database' AND table_schema = 'public'
    ↓
    返回字段列表（示例）:
    - year: character varying
    - scenario: character varying
    - function: character varying
    - year_total: numeric
    ↓
    确认: 使用小写字段名，数据类型为字符和数值型
    ↓
[Step 4: SQL模板选择]
    选择: 成本汇总查询模板
    ↓
[Step 5: SQL生成与执行]
    生成SQL:
    SELECT SUM(year_total) as total_budget
    FROM cost_database
    WHERE year = 'FY26'
      AND scenario = 'Budget1'
      AND function = 'HR';
    ↓
结果: [查询结果根据实际数据库返回]
```

### 关键说明

**为什么需要Step 3（查询表结构）？**

1. **避免字段名错误**: 不同数据库字段命名规范不同（小写/大写/驼峰）
2. **确认字段存在**: 避免使用不存在的字段（如误以为有 `department` 实际是 `function`）
3. **了解数据类型**: 数值计算时需要知道是 numeric/varchar/integer

**错误示例（跳过Step 3）**:
```sql
-- 错误：使用了大写字段名和方括号（SQL Server风格）
SELECT SUM([Year_Total]) FROM [Cost_Database] WHERE [Year] = 'FY26'

-- 正确：使用实际的小写字段名（PostgreSQL风格）
SELECT SUM(year_total) FROM cost_database WHERE year = 'FY26'
```

## 查询类型与SQL映射

### 类型1: 成本查询

**问题模式**: "[时间] [职能] [版本] 费用多少？"

**示例**:
- "FY26 HR预算多少？"
- "FY25 Procurement实际费用？"

**SQL模板**: 模板1（成本汇总查询）

### 类型2: 分摊查询

**问题模式**: "[时间] [职能] 分摊给 [目标] 的费用？"

**示例**:
- "FY25 IT分摊给CT的费用？"
- "FY26 HR分摊给成本中心412001的费用？"

**SQL模板**: 模板2（分摊金额计算）

### 类型3: 对比查询

**问题模式**: "[时间A] [版本A] 与 [时间B] [版本B] 比变化多少？"

**示例**:
- "FY26采购预算和FY25实际比变化多少？"
- "FY25 HR预算与实际差异？"

**SQL模板**: 模板3（预算对比）+ 变化计算公式

## 脚本结构

```
skills/finance/
├── SKILL.md              # 本文件 - 技能定义与规则
├── scripts/
│   ├── __init__.py
│   └── sql_query.py      # 核心：SQL执行引擎
└── references/           # (可选) 补充文档
```

### 核心脚本: sql_query.py

提供 `run_sql_query(sql: str) -> str` 函数，返回 JSON 格式结果：

```json
{
  "truncated": false,
  "limit": 200,
  "rows": [...]
}
```

## 环境配置

```bash
# 数据库连接参数
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cost_allocation
DB_USER=postgres
DB_PASSWORD=123456
```

依赖: `pip install psycopg2-binary`
