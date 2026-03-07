# 示例库与使用示例

## 三、内置问题 - SQL 示例库

**Q2：FY26 计划了多少 HR 费用预算？**

需求特征：筛选指定 year/scenario/function，先查明细，再单独聚合总金额。

SQL 生成流程：
1. 查询 cost_database 表结构确认字段
2. 生成聚合 SQL：
   ```sql
   SELECT SUM(year_total) as total
   FROM cost_database
   WHERE year = 'FY26' AND scenario = 'Budget1' AND function = 'HR'
   ```

---

### 3.2 复杂分摊计算类（跨表关联）

**Q3：FY25 实际分摊给 CT 的 IT 费用是多少？**

需求特征：主表 + 规则表四重关联，按 bl 字段筛选分摊主体。

核心计算逻辑：
```sql
SELECT
    cdb.month,
    (cdb.amount * rt.rate_no / 100.0) as allocated_amount
FROM cost_database cdb
JOIN rate_table rt ON cdb.month = rt.month
    AND cdb.year = rt.year
    AND cdb.scenario = rt.scenario
    AND cdb.key = rt.key
WHERE cdb.year = 'FY25'
  AND cdb.scenario = 'Actual'
  AND cdb.function = 'IT Allocation'
  AND rt.bl = 'CT'
```

---

**Q4：分摊给 413001 的 HR 费用变化 (FY26 BGT vs FY25 Actual)**

需求特征：双表联查 + CC 字段优先筛选，跨 Year/Scenario 对比。

执行步骤：
1. 查询 cost_database 和 rate_table 表结构
2. 生成 FY26 Budget 分摊 SQL
3. 生成 FY25 Actual 分摊 SQL
4. 分别执行获取结果
5. 在 Python 中对比计算变化额和变化率

---

### 3.3 同比/环比分析与趋势类

**Q5：采购费用从 FY25 Actual 到 FY26 BGT 的变化？**

需求特征：跨周期对比 + 变化额/变化率计算。

执行步骤：
1. 分别查询 FY26 Budget 和 FY25 Actual 的 Procurement 费用
2. 计算变化值和变化率
3. 输出对比结论

---

**Q6：HR 费用的月度趋势如何？**

需求特征：CTE + 月度汇总 + 环比增长率计算。

---

**Q7：26 财年预算分摊给 413001 的 HR 费用和 25 财年实际分摊给 XP 的 HR 费用对比**

需求特征：不同周期 + 不同分摊维度（CC/BL）对比。

核心逻辑：
- CC 号 413001、BL 值 XP 分别作为不同周期的筛选条件
- 元数据中 BL 与 CC 是一对多关系
- 若 CC 号包含在 BL 范围内则以 CC 号作为筛选字段

---

## SQL 生成原则

1. **先查表结构**：生成业务 SQL 前，先执行表结构查询
2. **使用小写字段**：PostgreSQL 字段名为小写，无需方括号
3. **四重关联**：分摊计算必须按 year/scenario/key/month 四重关联
4. **结果分析**：复杂对比在 Python 中完成，不依赖 SQL 输出最终结论
