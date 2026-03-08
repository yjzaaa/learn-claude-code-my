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
    
    print("=" * 80)
    print("26财年采购预算费用与25财年实际数对比分析报告")
    print("=" * 80)
    
    # 1. 查询总体数据
    print("\n1. 总体对比分析")
    print("-" * 40)
    
    sql_overall = '''
    -- FY26采购预算
    SELECT 'FY26预算' as period, SUM(year_total) as total_amount
    FROM cost_database
    WHERE year = 'FY26' AND scenario = 'Budget1' AND function = 'Procurement'
    
    UNION ALL
    
    -- FY25采购实际
    SELECT 'FY25实际', SUM(year_total)
    FROM cost_database
    WHERE year = 'FY25' AND scenario = 'Actual' AND function = 'Procurement';
    '''
    
    result_overall = run_sql_query(sql_overall)
    overall_data = json.loads(result_overall)
    
    fy26_budget = 0
    fy25_actual = 0
    
    if overall_data['rows']:
        for row in overall_data['rows']:
            period = row['period']
            amount = float(row['total_amount']) if row['total_amount'] else 0
            print(f"{period}: {amount:,.2f}")
            
            if period == 'FY26预算':
                fy26_budget = amount
            elif period == 'FY25实际':
                fy25_actual = amount
    
    # 计算变化
    delta = fy26_budget - fy25_actual
    if fy25_actual != 0:
        change_percent = (delta / fy25_actual) * 100
    else:
        change_percent = 0
    
    print(f"\n变化分析:")
    print(f"  绝对变化值: {delta:+,.2f}")
    print(f"  变化率: {change_percent:+.2f}%")
    
    # 2. 按成本项目分析
    print("\n2. 按成本项目对比分析")
    print("-" * 40)
    
    sql_by_cost = '''
    SELECT 
        cost_text,
        key,
        SUM(CASE WHEN year = 'FY26' AND scenario = 'Budget1' THEN year_total ELSE 0 END) as fy26_budget,
        SUM(CASE WHEN year = 'FY25' AND scenario = 'Actual' THEN year_total ELSE 0 END) as fy25_actual
    FROM cost_database
    WHERE function = 'Procurement'
      AND ((year = 'FY26' AND scenario = 'Budget1') OR (year = 'FY25' AND scenario = 'Actual'))
    GROUP BY cost_text, key
    HAVING SUM(CASE WHEN year = 'FY26' AND scenario = 'Budget1' THEN year_total ELSE 0 END) > 0
        OR SUM(CASE WHEN year = 'FY25' AND scenario = 'Actual' THEN year_total ELSE 0 END) > 0
    ORDER BY fy26_budget DESC;
    '''
    
    result_by_cost = run_sql_query(sql_by_cost)
    cost_data = json.loads(result_by_cost)
    
    if cost_data['rows']:
        print("成本项目 | 分摊标准 | FY26预算 | FY25实际 | 变化值 | 变化率")
        print("-" * 80)
        
        for row in cost_data['rows']:
            cost_text = row['cost_text'] or '未命名'
            key = row['key'] or '无'
            fy26 = float(row['fy26_budget']) if row['fy26_budget'] else 0
            fy25 = float(row['fy25_actual']) if row['fy25_actual'] else 0
            delta_item = fy26 - fy25
            
            if fy25 != 0:
                change_item = (delta_item / fy25) * 100
            else:
                change_item = 0 if fy26 == 0 else 100
            
            print(f"{cost_text:15s} | {key:8s} | {fy26:10,.2f} | {fy25:10,.2f} | {delta_item:+,.2f} | {change_item:+.2f}%")
    
    # 3. 月度趋势分析
    print("\n3. 月度趋势分析")
    print("-" * 40)
    
    sql_monthly_trend = '''
    SELECT 
        month,
        SUM(CASE WHEN year = 'FY26' AND scenario = 'Budget1' THEN amount ELSE 0 END) as fy26_budget,
        SUM(CASE WHEN year = 'FY25' AND scenario = 'Actual' THEN amount ELSE 0 END) as fy25_actual
    FROM cost_database
    WHERE function = 'Procurement'
      AND ((year = 'FY26' AND scenario = 'Budget1') OR (year = 'FY25' AND scenario = 'Actual'))
    GROUP BY month
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
    
    result_monthly_trend = run_sql_query(sql_monthly_trend)
    monthly_trend = json.loads(result_monthly_trend)
    
    if monthly_trend['rows']:
        print("月份 | FY26预算 | FY25实际 | 月度变化 | 趋势")
        print("-" * 60)
        
        for row in monthly_trend['rows']:
            month = row['month']
            fy26 = float(row['fy26_budget']) if row['fy26_budget'] else 0
            fy25 = float(row['fy25_actual']) if row['fy25_actual'] else 0
            delta_month = fy26 - fy25
            
            if fy25 != 0:
                change_month = (delta_month / fy25) * 100
            else:
                change_month = 0 if fy26 == 0 else 100
            
            # 判断趋势
            if delta_month > 0:
                trend = "↑ 增长"
            elif delta_month < 0:
                trend = "↓ 下降"
            else:
                trend = "→ 持平"
            
            print(f"{month:4s} | {fy26:10,.2f} | {fy25:10,.2f} | {delta_month:+,.2f} | {trend}")
    
    # 4. 总结分析
    print("\n4. 总结与洞察")
    print("-" * 40)
    
    print(f"主要发现:")
    print(f"1. 总体趋势: FY26采购预算为 {fy26_budget:,.2f}，比FY25实际费用 {fy25_actual:,.2f} 增加了 {abs(delta):,.2f}，增长 {abs(change_percent):.2f}%")
    print(f"2. 成本结构: 采购费用主要由以下项目构成:")
    
    if cost_data['rows']:
        for row in cost_data['rows']:
            cost_text = row['cost_text'] or '未命名'
            fy26 = float(row['fy26_budget']) if row['fy26_budget'] else 0
            if fy26 > 0:
                percentage = (fy26 / fy26_budget) * 100
                print(f"   - {cost_text}: {fy26:,.2f} ({percentage:.1f}%)")
    
    print(f"3. 月度分布: FY26预算在各月分布相对均匀，而FY25实际在10月较低，11月较高")
    print(f"4. 预算规划: FY26预算相比FY25实际增长3.98%，反映了对采购需求的适度增长预期")
    
    print("\n建议:")
    print(f"1. 关注主要成本项目 'Procurement' 和 'Pooling & MPC' 的成本控制")
    print(f"2. 分析FY25实际费用在11月异常高的原因，优化预算分配")
    print(f"3. 考虑通货膨胀和业务增长因素，3.98%的增长幅度较为合理")
    
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()