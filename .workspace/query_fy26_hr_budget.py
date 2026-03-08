import os
import sys
import json

sys.path.append('skills/finance/scripts')
from sql_query import run_sql_query

# 查询FY26 HR预算 - 按照finance技能文档中的模板
sql = """
SELECT 
    function,
    cost_text,
    key,
    SUM(year_total) as total_budget
FROM cost_database
WHERE year = 'FY26'
  AND scenario = 'Budget1'
  AND function = 'HR'
GROUP BY function, cost_text, key
ORDER BY total_budget DESC;
"""

print("Querying FY26 HR budget...")
result = run_sql_query(sql)
data = json.loads(result)

print(f"\nFY26 HR Budget Summary:")
print("=" * 50)

if data['rows']:
    total_budget = 0
    for row in data['rows']:
        budget = float(row['total_budget']) if row['total_budget'] else 0
        total_budget += budget
        print(f"{row['cost_text']} ({row['key']}): ¥{budget:,.2f}")
    
    print("=" * 50)
    print(f"Total HR Budget for FY26: ¥{total_budget:,.2f}")
else:
    print("No HR budget data found for FY26")
    
    # 让我们检查一下有哪些年份和场景的数据
    print("\nChecking available data...")
    check_sql = """
    SELECT DISTINCT year, scenario, function
    FROM cost_database
    WHERE function LIKE '%HR%'
    ORDER BY year, scenario, function;
    """
    
    check_result = run_sql_query(check_sql)
    check_data = json.loads(check_result)
    
    if check_data['rows']:
        print("\nAvailable HR-related data:")
        for row in check_data['rows']:
            print(f"  Year: {row['year']}, Scenario: {row['scenario']}, Function: {row['function']}")
    else:
        print("No HR-related data found in the database")