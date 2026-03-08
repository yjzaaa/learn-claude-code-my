import sys
import os

# 添加技能目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
skills_dir = os.path.join(project_root, 'skills/finance/scripts')
sys.path.append(skills_dir)

from sql_query import run_sql_query

# 1. 查询表结构
print("=== 查询表结构 ===")
table_structure_sql = """
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'cost_database' 
  AND table_schema = 'public' 
ORDER BY ordinal_position;
"""
result = run_sql_query(table_structure_sql)
print(result)

# 2. 查询FY25采购实际费用
print("\n=== 查询FY25采购实际费用 ===")
fy25_actual_sql = """
SELECT 
    function,
    cost_text,
    key,
    SUM(amount) as total_amount,
    SUM(year_total) as year_total_sum
FROM cost_database
WHERE year = 'FY25'
  AND scenario = 'Actual'
  AND function = 'Procurement'
GROUP BY function, cost_text, key
ORDER BY total_amount DESC;
"""
result = run_sql_query(fy25_actual_sql)
print(result)

# 3. 查询FY26采购预算费用
print("\n=== 查询FY26采购预算费用 ===")
fy26_budget_sql = """
SELECT 
    function,
    cost_text,
    key,
    SUM(amount) as total_amount,
    SUM(year_total) as year_total_sum
FROM cost_database
WHERE year = 'FY26'
  AND scenario = 'Budget1'
  AND function = 'Procurement'
GROUP BY function, cost_text, key
ORDER BY total_amount DESC;
"""
result = run_sql_query(fy26_budget_sql)
print(result)

# 4. 查询汇总数据用于对比
print("\n=== 查询汇总数据用于对比 ===")
comparison_sql = """
-- FY25采购实际费用汇总
SELECT 'FY25 Actual' as period, SUM(year_total) as total_cost
FROM cost_database
WHERE year = 'FY25' AND scenario = 'Actual' AND function = 'Procurement'

UNION ALL

-- FY26采购预算费用汇总
SELECT 'FY26 Budget', SUM(year_total)
FROM cost_database
WHERE year = 'FY26' AND scenario = 'Budget1' AND function = 'Procurement';
"""
result = run_sql_query(comparison_sql)
print(result)