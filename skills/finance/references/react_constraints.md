# 规则与字典约束

## 一、核心元数据约束（必须严格遵守，无任何例外）

### 1.1 数据源规范

- 主表：cost_database（费用基础数据），别名统一用 cdb
- 规则表：rate_table（分摊比例），别名统一用 t7
- 严格禁止：使用临时表、视图、存储过程，仅生成单表 / 联表的原生 SELECT 语句（适配 sqlquery 工具执行规范）

### 1.2 字段处理强制规则

- 数值转换：所有 amount 字段必须执行 CAST(amount AS FLOAT) 转换，无隐式类型转换
- 空值处理：所有参与计算 / 输出的字段，必须用 COALESCE(值, 0) 做 0 值兜底，避免 sqlquery 执行返回空值
- 比例计算：rate_no 字段处理规则：
  - 数据库中 rate_no 存储为小数字符串格式（如 `"0.020800"` 表示 2.08%）
  - **直接使用 `CAST(rate_no AS NUMERIC)`，无需除以 100**
  - 极少数情况下若遇到百分数字符串（如 `"12.5%"`），才去 `%` 再 `/100`
  - 错误示例：`CAST(REPLACE(t7.rate_no, '%', '') AS FLOAT) / 100`（会导致结果缩小 100 倍）
  - 正确示例：`CAST(t7.rate_no AS NUMERIC)`
- 维度优先级：比例关联时优先使用 cc 字段，bl 仅作为业务线辅助维度，无 CC 值时才允许使用 BL；CC/BL 与业务主体的对应关系：cc 号在 Bl 的范围内则直接取 CC 的值进行筛选

### 1.3 输出语法强制规范（适配 sqlquery 工具执行）

- 单语句原则：仅生成单条 SELECT 语句（复杂对比 / 趋势用 CTE 实现），禁止分号分隔的多语句，确保 sqlquery 工具一次执行
- 字段显式声明：所有表字段、别名字段（语义化命名）必须用 **""** 包裹（PostgreSQL语法），无任何裸字段；别名优先用英文（如 "Service_Content"），复杂计算用中文（如 "分摊金额"）
- 排序限制：ORDER BY 子句仅能使用 SELECT 结果集中的显式声明字段 / 别名，禁止使用表原始字段 / 数字索引；月度排序统一通过 month_num 数字值实现
- 聚合一致性：聚合查询必须保证 GROUP BY 子句包含 SELECT 中所有非聚合字段，避免 sqlquery 执行报聚合函数错误
- 别名统一：主表别名固定 cdb，规则表别名固定 t7，联合查询结果别名固定 combined_result，CTE 表按功能命名（如 base_cost/monthly_cost）

### 1.4 字段值强制约束（核心合规要求）

所有 SQL 语句中使用的字段值（WHERE 筛选值、关联匹配值等），必须是表 - 字段 - 部分字段值数据结构字典中已存在的有效值，禁止使用字典外任何值；若用户查询含字典外值，自动按字典有效值适配后再生成 SQL，确保 sqlquery 执行无无效值筛选错误。

补充规则：当从用户问题中解析出的参数并非具体值（如模糊描述、范围、别名或同义词）时，需先进行模糊匹配与字典映射，确定字典中的有效值后再生成 SQL；不得直接在 SQL 中使用不确定或字典外的值。

补充示例：类似“7092”这类不完整编号应视为模糊关键词，先在字典中做模糊匹配（如包含/前缀），映射到具体有效值后再生成 SQL。

```sql
   like '%7092%'
```

## 二、固定数据结构字典（关联 / 筛选 / 计算的唯一依据）

### 2.1 费用主表（cost_database）核心字段

- 维度字段：year、scenario（仅 Budget/Actual/Budget1）、function、month（精确匹配）、"Cost text"、key（分摊依据，必填）
- 计算字段：amount（必须 CAST 转换）、"Year Total"
- 关键约束：scenario 严格匹配版本（Budget/Actual/Budget1），month 为月度值需精确匹配字典有效值
- Scenario 强约束：
  - SQL 仅允许 `Budget1` / `Actual` / `Budget`
  - 用户输入 `BGT` / `Budget` / `预算` / `计划` 时，必须归一化为 `Budget1`
  - 禁止 SQL 中出现 `Scenario = 'BGT'`

### 2.2 分摊规则表（rate_table）核心字段

- 关联字段：year、scenario、month、key（与主表四重关联核心字段）
- 比例字段：rate_no（需去 % 转小数）、cc（优先使用）、bl（业务线辅助维度）
- 业务规则：仅当 cc 无值 / 不满足筛选时，才可使用 bl 做辅助维度筛选 / 分组；CC 号在 BL 范围内时，直接取 CC 值筛选

### 2.3 表关联核心条件（双表联查专用）

分摊计算场景需双表联查时（必须是涉及到多个部门才需要联表），必须使用四重精确匹配关联条件，无任何缺省，关联顺序统一如下：

```

cdb.year = t7.year AND cdb.scenario = t7.scenario AND cdb.key = t7.key AND cdb.month = t7.month
```

关联字段值均需为字典有效值，确保 sqlquery 执行关联无笛卡尔积、无无效匹配；联表类型优先用 LEFT JOIN（保留无比例主表数据）。

### 2.6 Allocation 场景固定映射（强约束）

- 若问题是 IT 分摊金额（allocated IT / IT allocation to ...），必须使用：
  - `cdb.function = 'IT Allocation'`
  - `cdb.key = '480056 Cycle'`
- 若问题是 HR 分摊金额（HR allocation to ...），必须使用：
  - `cdb.function = 'HR Allocation'`
  - `cdb.key = '480055 Cycle'`
- Allocation Function 强约束：
  - 分摊题禁止使用 `cdb.function = 'IT'` 或 `cdb.function = 'HR'`
  - 只有非分摊普通费用题，才允许 `IT` / `HR` Function
- 计算必须按月执行：`CAST(cdb.amount AS FLOAT) * normalized_rate_no`，再汇总到年。
- `normalized_rate_no` 统一规则：
  - **数据库中 RateNo 存储为小数字符串（如 `"0.020800"` = 2.08%）**
  - **直接使用 `CAST(rate_no AS NUMERIC)`，无需除以 100**
  - 若遇到百分数字符串（如 `"12.5%"`，极少见）才去 `%` 再 `/100`

### 2.4 表 - 字段 - 部分字段值数据结构字典（字段值唯一校验依据）

```
{{#1769654593187.result#}}
```

所有字段值必须严格匹配此字典，无字典外值出现在 SQL 中。

### 2.5 字段解释（来源：字段解释.md）

```
表名 字段名(值) 解释
SME_FI_InsightBot_CostDataBase Year 年份，年度，财年
SME_FI_InsightBot_CostDataBase Scenario 版本
SME_FI_InsightBot_CostDataBase Budget1 BGT, Budget, BGT1，预算
SME_FI_InsightBot_CostDataBase Actual Act，实际数
SME_FI_InsightBot_CostDataBase Function 费用类型，费用大类，费用产生自哪个职能部门
SME_FI_InsightBot_CostDataBase Cost text 服务项，合同内容，服务内容，服务名称
SME_FI_InsightBot_CostDataBase Account 总账科目
SME_FI_InsightBot_CostDataBase Category 成本类型，成本分类
SME_FI_InsightBot_CostDataBase Functional Cost 直接入Global function cost center的cost，也称为Global function cost
SME_FI_InsightBot_CostDataBase Cost Center Cost 直接入BL cost center 的cost，区分与Global Function cost
SME_FI_InsightBot_CostDataBase Key 按什么来分摊，分摊的依据，分摊标准，用什么来分摊
SME_FI_InsightBot_CostDataBase Month(Oct) 10月份发生的费用，和Year合起来看，就知道是具体哪一个月份
SME_FI_InsightBot_CostDataBase Month(Nov) 11月份发生的费用，和Year合起来看，就知道是具体哪一个月份
SME_FI_InsightBot_CostDataBase Month(Dec) 12月份发生的费用，和Year合起来看，就知道是具体哪一个月份
SME_FI_InsightBot_CostDataBase Month(Jan) 1月份发生的费用，和Year合起来看，就知道是具体哪一个月份
SME_FI_InsightBot_CostDataBase Month(Feb) 2月份发生的费用，和Year合起来看，就知道是具体哪一个月份
SME_FI_InsightBot_CostDataBase Month(Mar) 3月份发生的费用，和Year合起来看，就知道是具体哪一个月份
SME_FI_InsightBot_CostDataBase Month(Apr) 4月份发生的费用，和Year合起来看，就知道是具体哪一个月份
SME_FI_InsightBot_CostDataBase Month(May) 5月份发生的费用，和Year合起来看，就知道是具体哪一个月份
SME_FI_InsightBot_CostDataBase Month(Jun) 6月份发生的费用，和Year合起来看，就知道是具体哪一个月份
SME_FI_InsightBot_CostDataBase Month(Jul) 7月份发生的费用，和Year合起来看，就知道是具体哪一个月份
SME_FI_InsightBot_CostDataBase Month(Aug) 8月份发生的费用，和Year合起来看，就知道是具体哪一个月份
SME_FI_InsightBot_CostDataBase Month(Sep) 9月份发生的费用，和Year合起来看，就知道是具体哪一个月份
SME_FI_InsightBot_CostDataBase Year Total 汇总12个月份的数字，全年的金额
rate_table Year 财年
rate_table Scenario 版本
rate_table Month 所属期，所属月份，全年总计
rate_table Key Key的名字，就是Cost页的Key，分摊逻辑名称
rate_table CC cost center，成本中心
rate_table BL 部门，业务线
rate_table RateNo 代表某一个月某一个成本中心（列），用某一个分摊依据（行）分摊时的比例是多少
```

## 缩写与术语对照

- WCW -> White Collar Worker（白领）
- headcount -> 人头、人数
- Win Acc -> Windows 账号、电脑账号
- Key -> 分摊标准
- Procurement -> 采购部门
- IM indirect material -> 间接物料
- actual -> 实际
- budget1 -> 预算、计划
- Rolling Forecast2 FC2 -> 预算、计划
- SW -> 软件
