---
name: finance
description: 回答财务数据分析问题，包括费用查询、IT/HR分摊计算、预算实际对比分析、趋势分析等。当用户询问费用、分摊、预算、实际、对比等财务相关问题时触发。
---

# Finance 技能

回答 SSME_FI_InsightBot 数据库的财务数据分析问题。

## 快速判断问题类型

| 关键词 | 类型 | 必读文件 |
|-------|------|---------|
| "分摊给/至/到", "allocated to" | **分摊题** | `references/react_constraints.md` 第2.6节 |
| "对比", "vs", "差异" | 对比分析 | `references/react_examples.md` |
| "趋势", "变化", "增长" | 趋势分析 | `references/react_examples.md` |
| "费用", "amount" | 普通查询 | `references/react_rules.md` |

## 核心规则

### ⚠️ 表名警告（常见错误）
- ✅ **正确表名**: `cost_database` (费用数据主表), `rate_table` (分摊率表), `cc_mapping` (成本中心映射)
- ❌ **错误**: `cost_allocation` 是数据库名，不是表名！

### 分摊题强制规则（必须遵守）
- 使用 `cdb.function = 'IT Allocation'` 或 `'HR Allocation'`
- **禁止**使用 `'IT'` 或 `'HR'`（这是常见错误）
- 必须双表联查：`cost_database` (cdb) + `rate_table` (rt)
- 分摊金额 = `amount * rate_no`

### 金额符号含义
- **负数** = 分摊出去（贷方）
- **正数** = 分摊进来（借方）

### SQL语法规范
- 表别名: `cdb` = cost_database, `rt` = rate_table
- 字段名: 小写，无方括号 (PostgreSQL)
- 数值转换: `CAST(amount AS NUMERIC)`

## 回答流程

1. **问题分类** → 看上表确定类型
2. **读取约束** → 分摊题必读 `react_constraints.md`
3. **生成SQL** → 参考 `react_examples.md` 中的示例
4. **执行查询** → 使用 `run_sql_query`
5. **回答用户** → 解释结果（注意金额符号含义）

## 参考文件导航

| 文件 | 何时读取 | 内容 |
|-----|---------|------|
| `references/react_constraints.md` | **分摊题必须读** | 分摊计算约束、Key映射、强制规则 |
| `references/react_rules.md` | 提取参数时 | 字段映射、同义词归一化 |
| `references/react_examples.md` | 生成SQL时 | 各类问题的SQL示例 |
| `references/sql_templates.md` | 需要模板时 | 标准SQL模板 |
| `references/module_map.md` | 查表结构时 | 数据库表结构说明 |

## 示例

**用户**: "25财年实际分摊给CT的IT费用是多少？"

**处理**:
1. 关键词 "分摊给" → 分摊题
2. 读 `react_constraints.md` → IT Allocation Key = '480056 Cycle'
3. 读 `react_examples.md` → 找到IT分摊到BL示例
4. 生成SQL执行
5. 结果负数 → 说明是"分摊出去的费用"
