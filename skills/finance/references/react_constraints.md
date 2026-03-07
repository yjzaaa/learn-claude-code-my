# 规则与字典约束

## 一、核心元数据约束（必须严格遵守，无任何例外）

### 1.1 数据源规范

- 主表：`cost_database`（费用基础数据），别名统一用 cdb
- 规则表：`rate_table`（分摊比例），别名统一用 rt
- 严格禁止：使用临时表、视图、存储过程，仅生成单表 / 联表的原生 SELECT 语句

### 1.2 字段处理强制规则

- 数值转换：所有数值字段（如 amount, rate_no）根据实际数据类型处理，无需强制 CAST
- 空值处理：所有参与计算 / 输出的字段，用 COALESCE(值, 0) 做 0 值兜底
- 比例计算：`rate_no` 字段直接使用（已是小数或百分比数值）
- 维度优先级：比例关联时优先使用 `cc` 字段，`bl` 仅作为业务线辅助维度

### 1.3 输出语法强制规范

- 单语句原则：仅生成单条 SELECT 语句（复杂对比 / 趋势用 CTE 实现），禁止分号分隔的多语句
- 字段命名：所有表字段直接使用小写字段名，无需方括号包裹
- 排序限制：ORDER BY 子句使用 SELECT 结果集中的字段 / 别名；月度排序通过 month 字段或数字实现
- 聚合一致性：聚合查询保证 GROUP BY 包含 SELECT 中所有非聚合字段
- 别名统一：主表别名固定 cdb，规则表别名固定 rt，CTE 表按功能命名

### 1.4 字段值强制约束

所有 SQL 语句中使用的字段值必须是数据库中存在的有效值；若用户查询含模糊值，自动适配后再生成 SQL。

补充规则：模糊关键词先做模糊匹配（如包含/前缀），映射到具体有效值后再生成 SQL。

```sql
like '%关键词%'
```

## 二、固定数据结构字典

### 2.1 费用主表（cost_database）核心字段

- 维度字段：year, scenario（Budget1/Actual）, function, month, cost_text, key
- 计算字段：amount, year_total
- 关键约束：scenario 严格匹配版本（Budget1/Actual）
- Scenario 强约束：
  - SQL 仅允许 `Budget1` / `Actual`
  - 用户输入 `BGT` / `Budget` / `预算` 时，必须归一化为 `Budget1`
  - 禁止 SQL 中出现 `scenario = 'BGT'`

### 2.2 分摊规则表（rate_table）核心字段

- 关联字段：year, scenario, month, key（与主表四重关联）
- 比例字段：rate_no, cc（优先使用）, bl（业务线辅助维度）
- 业务规则：仅当 cc 无值时，才可使用 bl 做辅助维度

### 2.3 表关联核心条件

分摊计算场景双表联查时，使用四重精确匹配：

```sql
cdb.year = rt.year AND cdb.scenario = rt.scenario AND cdb.key = rt.key AND cdb.month = rt.month
```

联表类型优先用 LEFT JOIN。

### 2.4 Allocation 场景固定映射

- IT 分摊金额：
  - `cdb.function = 'IT Allocation'`
  - `cdb.key = '480056 Cycle'`
- HR 分摊金额：
  - `cdb.function = 'HR Allocation'`
  - `cdb.key = '480055 Cycle'`
- 分摊题禁止使用 `cdb.function = 'IT'` 或 `cdb.function = 'HR'`
- 计算必须按月执行：`cdb.amount * (rt.rate_no / 100)`，再汇总到年

### 2.5 字段解释

| 表名 | 字段 | 解释 |
|------|------|------|
| cost_database | year | 年份，年度，财年 |
| cost_database | scenario | 版本（Budget1/Actual） |
| cost_database | function | 费用类型，职能部门 |
| cost_database | cost_text | 服务项，合同内容 |
| cost_database | key | 分摊依据，分摊标准 |
| cost_database | month | 月份（Jan-Dec） |
| cost_database | amount | 月度金额 |
| cost_database | year_total | 全年金额 |
| rate_table | year | 财年 |
| rate_table | scenario | 版本 |
| rate_table | month | 所属月份 |
| rate_table | key | 分摊逻辑名称 |
| rate_table | cc | 成本中心 |
| rate_table | bl | 业务线 |
| rate_table | rate_no | 分摊比例 |

## 缩写与术语对照

- WCW -> White Collar Worker（白领）
- headcount -> 人头、人数
- Win Acc -> Windows 账号
- Key -> 分摊标准
- Procurement -> 采购部门
- IM -> indirect material（间接物料）
- actual -> 实际
- budget1 -> 预算、计划
- SW -> 软件
