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
    
    print("查询FY26采购预算费用...")
    # 查询FY26采购预算
    sql_fy26_budget = '''
    SELECT 
        SUM(year_total) as total_budget
    FROM cost_database
    WHERE year = 'FY26'
      AND scenario = 'Budget1'
      AND function = 'Procurement';
    '''
    
    result_fy26 = run_sql_query(sql_fy26_budget)
    print(f"FY26采购预算查询结果: {result_fy26}")
    
    print("\n查询FY25采购实际费用...")
    # 查询FY25采购实际
    sql_fy25_actual = '''
    SELECT 
        SUM(year_total) as total_actual
    FROM cost_database
    WHERE year = 'FY25'
      AND scenario = 'Actual'
      AND function = 'Procurement';
    '''
    
    result_fy25 = run_sql_query(sql_fy25_actual)
    print(f"FY25采购实际查询结果: {result_fy25}")
    
    # 解析结果
    fy26_data = json.loads(result_fy26)
    fy25_data = json.loads(result_fy25)
    
    if fy26_data['rows'] and fy25_data['rows']:
        fy26_budget = float(fy26_data['rows'][0]['total_budget']) if fy26_data['rows'][0]['total_budget'] else 0
        fy25_actual = float(fy25_data['rows'][0]['total_actual']) if fy25_data['rows'][0]['total_actual'] else 0
        
        print(f"\n=== 分析结果 ===")
        print(f"FY26采购预算费用: {fy26_budget:,.2f}")
        print(f"FY25采购实际费用: {fy25_actual:,.2f}")
        
        # 计算变化
        delta = fy26_budget - fy25_actual
        if fy25_actual != 0:
            change_percent = (delta / fy25_actual) * 100
        else:
            change_percent = 0
            
        print(f"变化值: {delta:+,.2f}")
        print(f"变化率: {change_percent:+.2f}%")
        
        # 分析结论
        if delta > 0:
            print(f"结论: FY26采购预算比FY25实际费用增加了 {abs(delta):,.2f}，增长 {abs(change_percent):.2f}%")
        elif delta < 0:
            print(f"结论: FY26采购预算比FY25实际费用减少了 {abs(delta):,.2f}，下降 {abs(change_percent):.2f}%")
        else:
            print("结论: FY26采购预算与FY25实际费用持平")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()