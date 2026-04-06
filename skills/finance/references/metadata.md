# 业务元数据（精简）

> 仅维护业务表名映射与意图/关键词到表的映射。
> 表结构由数据源中间件按需从数据库自动获取，元数据不包含字段级结构。

```json
{
  "tables": [
    "cost_database",
    "rate_table",
    "SSME_FI_InsightBot_CCMapping"
  ],
  "default_tables": ["cost_database"],
  "intent_table_map": {
    "allocation": [
      "cost_database",
      "rate_table"
    ],
    "budget_vs_actual": ["cost_database"],
    "variance": ["cost_database"],
    "trend": ["cost_database"],
    "cost_structure": ["cost_database"],
    "profitability": ["cost_database"]
  },
  "keyword_table_map": {
    "分摊": ["cost_database", "rate_table"],
    "allocation": [
      "cost_database",
      "rate_table"
    ],
    "预算": ["cost_database"],
    "实际": ["cost_database"],
    "差异": ["cost_database"],
    "同比": ["cost_database"],
    "环比": ["cost_database"],
    "趋势": ["cost_database"],
    "对比": ["cost_database"],
    "成本": ["cost_database"],
    "费用": ["cost_database"],
    "服务": ["cost_database"],
    "it": ["cost_database"],
    "IT": ["cost_database"],
    "it服务": ["cost_database"],
    "IT服务": ["cost_database"],
    "利润": ["cost_database"],
    "收入": ["cost_database"],
    "费率": ["rate_table"],
    "比例": ["rate_table"]
  }
}
```
