import os
import sys
import json

sys.path.append('skills/finance/scripts')
from sql_query import run_sql_query

# 查询HR Allocation（HR分摊费用）
sql = """
SELECT 
    function,
    cost_text,
    category,
    account,
    key,
    SUM(year_total) as total_budget
FROM cost_database
WHERE year = 'FY26'
  AND scenario = 'Budget1'
  AND function = 'HR Allocation'
GROUP BY function, cost_text, category, account, key
ORDER BY total_budget DESC;
"""

print("Querying FY26 HR Allocation budget...")
result = run_sql_query(sql)
data = json.loads(result)

print(f"\nFY26 HR Allocation Budget:")
print("=" * 70)

if data['rows']:
    total_allocation = 0
    for row in data['rows']:
        budget = float(row['total_budget']) if row['total_budget'] else 0
        total_allocation += budget
        
        cost_text = row['cost_text'] or "N/A"
        category = row['category'] or "N/A"
        account = row['account'] or "N/A"
        key = row['key'] or "N/A"
        
        print(f"{cost_text} | {category} | {account} | {key}: {budget:,.2f}")
    
    print("=" * 70)
    print(f"Total HR Allocation Budget for FY26: {total_allocation:,.2f}")
    
    # 查询总的HR相关预算（HR + HR Allocation）
    print(f"\nChecking total HR-related budget...")
    total_sql = """
    SELECT 
        function,
        SUM(year_total) as total
    FROM cost_database
    WHERE year = 'FY26'
      AND scenario = 'Budget1'
      AND function IN ('HR', 'HR Allocation')
    GROUP BY function
    ORDER BY function;
    """
    
    total_result = run_sql_query(total_sql)
    total_data = json.loads(total_result)
    
    if total_data['rows']:
        grand_total = 0
        print(f"\nBreakdown by Function:")
        for row in total_data['rows']:
            func_total = float(row['total']) if row['total'] else 0
            grand_total += func_total
            print(f"  {row['function']}: {func_total:,.2f}")
        
        print(f"  {'-' * 40}")
        print(f"  Grand Total: {grand_total:,.2f}")
else:
    print("No HR Allocation budget data found for FY26")