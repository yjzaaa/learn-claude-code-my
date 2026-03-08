import os
import sys
import json

sys.path.append('skills/finance/scripts')
from sql_query import run_sql_query

# 查询更详细的FY26 HR预算数据
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
  AND function = 'HR'
GROUP BY function, cost_text, category, account, key
ORDER BY total_budget DESC;
"""

print("Querying detailed FY26 HR budget...")
result = run_sql_query(sql)
data = json.loads(result)

print(f"\nDetailed FY26 HR Budget Analysis:")
print("=" * 70)

if data['rows']:
    total_budget = 0
    categories = {}
    
    for row in data['rows']:
        budget = float(row['total_budget']) if row['total_budget'] else 0
        total_budget += budget
        
        category = row['category'] or "Uncategorized"
        if category not in categories:
            categories[category] = 0
        categories[category] += budget
        
        cost_text = row['cost_text'] or "N/A"
        account = row['account'] or "N/A"
        key = row['key'] or "N/A"
        
        print(f"{cost_text} | {category} | {account} | {key}: {budget:,.2f}")
    
    print("=" * 70)
    print(f"\nTotal HR Budget for FY26: {total_budget:,.2f}")
    
    print(f"\nBudget by Category:")
    for category, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / total_budget) * 100 if total_budget > 0 else 0
        print(f"  {category}: {amount:,.2f} ({percentage:.1f}%)")
    
    # 检查是否有月度数据
    print(f"\nChecking monthly breakdown...")
    monthly_sql = """
    SELECT 
        month,
        SUM(amount) as monthly_amount
    FROM cost_database
    WHERE year = 'FY26'
      AND scenario = 'Budget1'
      AND function = 'HR'
      AND month IS NOT NULL
    GROUP BY month
    ORDER BY month;
    """
    
    monthly_result = run_sql_query(monthly_sql)
    monthly_data = json.loads(monthly_result)
    
    if monthly_data['rows']:
        print(f"\nMonthly HR Budget Distribution:")
        monthly_total = 0
        for row in monthly_data['rows']:
            monthly_amount = float(row['monthly_amount']) if row['monthly_amount'] else 0
            monthly_total += monthly_amount
            print(f"  Month {row['month']}: {monthly_amount:,.2f}")
        
        if abs(monthly_total - total_budget) > 0.01:
            print(f"  Note: Monthly total ({monthly_total:,.2f}) differs from annual total")
else:
    print("No detailed HR budget data found for FY26")