import os
import sys

# 设置数据库连接参数
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'cost_allocation'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = '123456'
os.environ['DB_PORT'] = '5432'

# 添加技能脚本路径
sys.path.append('skills/finance/scripts')

try:
    from sql_query import run_sql_query
    import json
    
    print("查询FY26采购预算详细数据...")
    # 查询FY26采购预算详细数据（按成本项目）
    sql_fy26_detail = '''
    SELECT 
        cost_text,
        key,
        SUM(year_total) as total_amount
    FROM cost_database
    WHERE year = 'FY26'
      AND scenario = 'Budget1'
      AND function = 'Procurement'
    GROUP BY cost_text, key
    ORDER BY total_amount DESC;
    '''
    
    result_fy26_detail = run_sql_query(sql_fy26_detail)
    print(f"FY26采购预算详细查询结果: {result_fy26_detail}")
    
    print("\n查询FY25采购实际详细数据...")
    # 查询FY25采购实际详细数据（按成本项目）
    sql_fy25_detail = '''
    SELECT 
        cost_text,
        key,
        SUM(year_total) as total_amount
    FROM cost_database
    WHERE year = 'FY25'
      AND scenario = 'Actual'
      AND function = 'Procurement'
    GROUP BY cost_text, key
    ORDER BY total_amount DESC;
    '''
    
    result_fy25_detail = run_sql_query(sql_fy25_detail)
    print(f"FY25采购实际详细查询结果: {result_fy25_detail}")
    
    # 解析详细结果
    fy26_detail = json.loads(result_fy26_detail)
    fy25_detail = json.loads(result_fy25_detail)
    
    print(f"\n=== FY26采购预算主要成本项目 ===")
    if fy26_detail['rows']:
        for i, row in enumerate(fy26_detail['rows'][:10], 1):  # 显示前10项
            cost_text = row['cost_text'] or '未命名'
            key = row['key'] or '无'
            amount = float(row['total_amount']) if row['total_amount'] else 0
            print(f"{i}. {cost_text} ({key}): {amount:,.2f}")
    
    print(f"\n=== FY25采购实际主要成本项目 ===")
    if fy25_detail['rows']:
        for i, row in enumerate(fy25_detail['rows'][:10], 1):  # 显示前10项
            cost_text = row['cost_text'] or '未命名'
            key = row['key'] or '无'
            amount = float(row['total_amount']) if row['total_amount'] else 0
            print(f"{i}. {cost_text} ({key}): {amount:,.2f}")
    
    # 查询月度数据对比
    print(f"\n=== 月度数据对比 ===")
    sql_monthly = '''
    SELECT 
        year,
        scenario,
        month,
        SUM(amount) as monthly_amount
    FROM cost_database
    WHERE function = 'Procurement'
      AND ((year = 'FY26' AND scenario = 'Budget1') OR (year = 'FY25' AND scenario = 'Actual'))
    GROUP BY year, scenario, month
    ORDER BY 
        CASE month
            WHEN 'Jan' THEN 1
            WHEN 'Feb' THEN 2
            WHEN 'Mar' THEN 3
            WHEN 'Apr' THEN 4
            WHEN 'May' THEN 5
            WHEN 'Jun' THEN 6
            WHEN 'Jul' THEN 7
            WHEN 'Aug' THEN 8
            WHEN 'Sep' THEN 9
            WHEN 'Oct' THEN 10
            WHEN 'Nov' THEN 11
            WHEN 'Dec' THEN 12
            ELSE 13
        END;
    '''
    
    result_monthly = run_sql_query(sql_monthly)
    monthly_data = json.loads(result_monthly)
    
    if monthly_data['rows']:
        print("月份 | FY26预算 | FY25实际 | 月度变化")
        print("-" * 50)
        
        # 按月份分组数据
        monthly_dict = {}
        for row in monthly_data['rows']:
            year = row['year']
            scenario = row['scenario']
            month = row['month']
            amount = float(row['monthly_amount']) if row['monthly_amount'] else 0
            
            if month not in monthly_dict:
                monthly_dict[month] = {'FY26_Budget': 0, 'FY25_Actual': 0}
            
            if year == 'FY26' and scenario == 'Budget1':
                monthly_dict[month]['FY26_Budget'] = amount
            elif year == 'FY25' and scenario == 'Actual':
                monthly_dict[month]['FY25_Actual'] = amount
        
        # 按月份顺序显示
        month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        for month in month_order:
            if month in monthly_dict:
                fy26 = monthly_dict[month]['FY26_Budget']
                fy25 = monthly_dict[month]['FY25_Actual']
                monthly_delta = fy26 - fy25
                print(f"{month:4s} | {fy26:10,.2f} | {fy25:10,.2f} | {monthly_delta:+,.2f}")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()