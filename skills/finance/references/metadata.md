# 业务元数据（精简）

> 仅维护业务表名映射与意图/关键词到表的映射。
> 表结构由数据源中间件按需从数据库自动获取，元数据不包含字段级结构。

```json
{
  "tables": [
    "SSME_FI_InsightBot_CostDataBase",
    "SSME_FI_InsightBot_Rate",
    "SSME_FI_InsightBot_CCMapping"
  ],
  "default_tables": ["SSME_FI_InsightBot_CostDataBase"],
  "intent_table_map": {
    "allocation": [
      "SSME_FI_InsightBot_CostDataBase",
      "SSME_FI_InsightBot_Rate"
    ],
    "budget_vs_actual": ["SSME_FI_InsightBot_CostDataBase"],
    "variance": ["SSME_FI_InsightBot_CostDataBase"],
    "trend": ["SSME_FI_InsightBot_CostDataBase"],
    "cost_structure": ["SSME_FI_InsightBot_CostDataBase"],
    "profitability": ["SSME_FI_InsightBot_CostDataBase"]
  },
  "keyword_table_map": {
    "分摊": ["SSME_FI_InsightBot_CostDataBase", "SSME_FI_InsightBot_Rate"],
    "allocation": [
      "SSME_FI_InsightBot_CostDataBase",
      "SSME_FI_InsightBot_Rate"
    ],
    "预算": ["SSME_FI_InsightBot_CostDataBase"],
    "实际": ["SSME_FI_InsightBot_CostDataBase"],
    "差异": ["SSME_FI_InsightBot_CostDataBase"],
    "同比": ["SSME_FI_InsightBot_CostDataBase"],
    "环比": ["SSME_FI_InsightBot_CostDataBase"],
    "趋势": ["SSME_FI_InsightBot_CostDataBase"],
    "对比": ["SSME_FI_InsightBot_CostDataBase"],
    "成本": ["SSME_FI_InsightBot_CostDataBase"],
    "费用": ["SSME_FI_InsightBot_CostDataBase"],
    "服务": ["SSME_FI_InsightBot_CostDataBase"],
    "it": ["SSME_FI_InsightBot_CostDataBase"],
    "IT": ["SSME_FI_InsightBot_CostDataBase"],
    "it服务": ["SSME_FI_InsightBot_CostDataBase"],
    "IT服务": ["SSME_FI_InsightBot_CostDataBase"],
    "利润": ["SSME_FI_InsightBot_CostDataBase"],
    "收入": ["SSME_FI_InsightBot_CostDataBase"],
    "费率": ["SSME_FI_InsightBot_Rate"],
    "比例": ["SSME_FI_InsightBot_Rate"]
  }
}
```
