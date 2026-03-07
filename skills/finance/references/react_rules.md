# 匹配规则与执行约束

## 四、需求匹配规则

基于用户查询核心诉求，自动识别 4 类需求类型，生成可执行的 SQL。

### 4.1 枚举查询

- 场景特征：筛选维度、枚举字段值，无计算/聚合
- 生成规则：单表查询 + DISTINCT 去重 + WHERE 筛选

### 4.2 聚合统计

- 场景特征：按维度分组，对 amount 求和/计数
- 生成规则：单表查询 + COALESCE(SUM(amount), 0) 聚合 + GROUP BY 维度字段
- 关键约束：GROUP BY 包含所有 SELECT 非聚合字段

### 4.3 分摊计算

- 场景特征：跨表关联计算分摊金额，核心逻辑「分摊金额 = 基础金额 × 分摊比例」
- 生成规则：主表 (cdb) + 规则表 (rt) 四重关联 + LEFT JOIN
- 核心计算：`cdb.amount * (rt.rate_no / 100)`
- 别名规范：分摊金额别名为 allocated_amount，基础金额别名为 base_cost
- 分组规则：按 year/scenario/function/分摊主体/month 分组

### 4.4 对比/趋势分析

- 场景特征：多版本/多周期对比，含变化率/环比计算
- 生成规则：使用 CTE 实现（基础数据 → 中间计算 → 结果合并）
- 计算要求：
  - 提取对比值、计算变化额/变化率
  - 包含除零/空值保护
  - 变化率保留 2 位小数
- 排序：月度排序通过 month 或数字值实现

## 五、异常处理机制

- 空值检查：所有计算字段用 COALESCE(值, 0) 兜底
- 除零保护：除法运算用 CASE WHEN 分母 = 0 THEN 0 ELSE 分子/分母 END
- 关联校验：双表联查使用 LEFT JOIN + 四重关联条件

## 六、SQL 执行适配规则

- 结果结构化：SELECT 字段语义化别名
- 单语句实现：通过单条 SELECT 语句（含 CTE）实现
- 排序合理：ORDER BY 使用显式字段/别名
- 无冗余内容：生成的内容仅为纯 SQL 语句

## 七、版本与兼容性

生成的 SQL 适用于 PostgreSQL 数据库。

## 八、最终执行流程

- 识别需求类型与维度
- 查询表结构确认字段
- 生成合规 SQL
- 执行并获取结果
- 完成汇总/对比/趋势分析
- 输出自然语言结论

## 九、业务规则摘要

- allocation_calculation: 分摊金额 = cost_amount * normalized_rate_no
- budget_actual_variance: Variance = Actual - Budget
- fiscal_year: 财年周期为 10 月至次年 9 月
- query_priority: 能明确到 CC 时优先按 CC 维度计算

### 强约束

- Scenario 归一化：用户表述 `BGT`/`Budget`/`预算` 一律映射为 `Budget1`
- IT Allocation 场景默认映射 key = `480056 Cycle`
- HR Allocation 场景默认映射 key = `480055 Cycle`
- Allocation Function 归一化：分摊题必须使用 `function = 'IT Allocation'` 或 `function = 'HR Allocation'`
- 分摊题必须按月先算 amount * rate 后做年度汇总
- 金额问法优先输出单值汇总；对比问法必须同时输出差额与变化率

## 缩写与术语对照

- WCW -> White Collar Worker
- headcount -> 人头、人数
- Win Acc -> Windows 账号
- Key -> 分摊标准
- Procurement -> 采购部门
- IM -> indirect material
- actual -> 实际
- budget1 -> 预算、计划
- SW -> 软件
