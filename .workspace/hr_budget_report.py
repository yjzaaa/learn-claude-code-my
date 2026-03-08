#!/usr/bin/env python3
"""Generate detailed HR budget report for FY26."""

import os
import sys
import json
sys.path.append('skills/finance/scripts')

# 设置环境变量
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_NAME', 'cost_allocation')
os.environ.setdefault('DB_USER', 'postgres')
os.environ.setdefault('DB_PASSWORD', '123456')
os.environ.setdefault('DB_PORT', '5432')

try:
    from sql_query import run_sql_query
except ImportError as e:
    print(f"Error importing sql_query: {e}")
    sys.exit(1)

def format_currency(amount):
    """格式化货币金额"""
    try:
        num = float(amount)
        return f"${num:,.2f}"
    except:
        return amount

def main():
    print("=" * 60)
    print("26财年HR费用预算报告")
    print("=" * 60)
    
    # 查询总预算
    sql_total = """
    SELECT SUM(year_total) as total_hr_budget_fy26
    FROM cost_database 
    WHERE year = 'FY26' 
      AND scenario = 'Budget1' 
      AND function = 'HR';
    """
    
    result_total = run_sql_query(sql_total)
    data_total = json.loads(result_total)
    
    if data_total['rows']:
        total_budget = data_total['rows'][0]['total_hr_budget_fy26']
        print(f"\n[总预算] 26财年HR费用总预算: {format_currency(total_budget)}")
    
    # 查询详细分类
    sql_detail = """
    SELECT 
        function,
        cost_text,
        key,
        SUM(amount) as monthly_total,
        SUM(year_total) as annual_total
    FROM cost_database 
    WHERE year = 'FY26' 
      AND scenario = 'Budget1' 
      AND function = 'HR'
    GROUP BY function, cost_text, key
    ORDER BY annual_total DESC;
    """
    
    result_detail = run_sql_query(sql_detail)
    data_detail = json.loads(result_detail)
    
    if data_detail['rows']:
        print("\n[详细分类] 预算详细分类:")
        print("-" * 60)
        print(f"{'项目':<20} {'年度预算':<20} {'月度预算':<20} {'分摊标准':<15}")
        print("-" * 60)
        
        for row in data_detail['rows']:
            cost_text = row['cost_text']
            annual = format_currency(row['annual_total'])
            monthly = format_currency(row['monthly_total'])
            key = row['key']
            print(f"{cost_text:<20} {annual:<20} {monthly:<20} {key:<15}")
    
    # 查询月度分布（可选）
    sql_monthly = """
    SELECT 
        month,
        SUM(amount) as monthly_amount
    FROM cost_database 
    WHERE year = 'FY26' 
      AND scenario = 'Budget1' 
      AND function = 'HR'
    GROUP BY month
    ORDER BY month;
    """
    
    result_monthly = run_sql_query(sql_monthly)
    data_monthly = json.loads(result_monthly)
    
    if data_monthly['rows']:
        print("\n[月度分布] 月度预算分布:")
        print("-" * 40)
        print(f"{'月份':<10} {'预算金额':<20}")
        print("-" * 40)
        
        for row in data_monthly['rows']:
            month = row['month']
            amount = format_currency(row['monthly_amount'])
            print(f"{month:<10} {amount:<20}")
    
    print("\n" + "=" * 60)
    print("报告生成完成")
    print("=" * 60)

if __name__ == "__main__":
    main()