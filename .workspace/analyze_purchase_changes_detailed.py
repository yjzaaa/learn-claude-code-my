import sys
import os

# 添加技能目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
skills_dir = os.path.join(project_root, 'skills/finance/scripts')
sys.path.append(skills_dir)

from sql_query import run_sql_query
import json

def format_currency(value):
    """格式化货币显示"""
    return f"¥{float(value):,.2f}"

def calculate_change(current, previous):
    """计算变化百分比"""
    if float(previous) == 0:
        return 0
    return ((float(current) - float(previous)) / float(previous)) * 100

def analyze_purchase_changes():
    """分析采购费用变化"""
    
    print("=" * 80)
    print("26财年采购预算费用与25财年实际数对比分析")
    print("=" * 80)
    
    # 1. 查询详细的对比数据
    print("\n1. 详细项目对比分析:")
    print("-" * 80)
    
    detailed_comparison_sql = """
    WITH fy25_data AS (
        SELECT 
            cost_text,
            key,
            SUM(year_total) as fy25_total
        FROM cost_database
        WHERE year = 'FY25' 
          AND scenario = 'Actual' 
          AND function = 'Procurement'
        GROUP BY cost_text, key
    ),
    fy26_data AS (
        SELECT 
            cost_text,
            key,
            SUM(year_total) as fy26_total
        FROM cost_database
        WHERE year = 'FY26' 
          AND scenario = 'Budget1' 
          AND function = 'Procurement'
        GROUP BY cost_text, key
    )
    SELECT 
        COALESCE(fy25.cost_text, fy26.cost_text) as cost_text,
        COALESCE(fy25.key, fy26.key) as key,
        COALESCE(fy25.fy25_total, 0) as fy25_actual,
        COALESCE(fy26.fy26_total, 0) as fy26_budget,
        COALESCE(fy26.fy26_total, 0) - COALESCE(fy25.fy25_total, 0) as amount_change,
        CASE 
            WHEN COALESCE(fy25.fy25_total, 0) = 0 THEN NULL
            ELSE ((COALESCE(fy26.fy26_total, 0) - COALESCE(fy25.fy25_total, 0)) / COALESCE(fy25.fy25_total, 0)) * 100
        END as percent_change
    FROM fy25_data fy25
    FULL OUTER JOIN fy26_data fy26 
        ON fy25.cost_text = fy26.cost_text AND fy25.key = fy26.key
    ORDER BY COALESCE(fy25.cost_text, fy26.cost_text);
    """
    
    result_json = run_sql_query(detailed_comparison_sql)
    result = json.loads(result_json)
    
    if result and 'rows' in result:
        total_fy25 = 0
        total_fy26 = 0
        
        print(f"{'成本项目':<20} {'Key':<10} {'FY25实际':>15} {'FY26预算':>15} {'金额变化':>15} {'变化率':>10}")
        print("-" * 85)
        
        for row in result['rows']:
            cost_text = row['cost_text']
            key = row['key']
            fy25_actual = float(row['fy25_actual'])
            fy26_budget = float(row['fy26_budget'])
            amount_change = float(row['amount_change'])
            percent_change = row['percent_change']
            
            total_fy25 += fy25_actual
            total_fy26 += fy26_budget
            
            if percent_change is None:
                percent_str = "N/A"
            else:
                try:
                    percent_float = float(percent_change)
                    percent_str = f"{percent_float:.1f}%"
                except:
                    percent_str = "N/A"
            
            print(f"{cost_text:<20} {key:<10} {format_currency(fy25_actual):>15} {format_currency(fy26_budget):>15} {format_currency(amount_change):>15} {percent_str:>10}")
        
        print("-" * 85)
        total_change = total_fy26 - total_fy25
        total_percent = calculate_change(total_fy26, total_fy25)
        
        print(f"{'总计':<20} {'':<10} {format_currency(total_fy25):>15} {format_currency(total_fy26):>15} {format_currency(total_change):>15} {total_percent:>9.1f}%")
    
    # 2. 查询月度数据趋势
    print("\n\n2. 月度数据趋势分析:")
    print("-" * 80)
    
    monthly_trend_sql = """
    WITH monthly_data AS (
        SELECT 
            year,
            scenario,
            month,
            SUM(year_total) as monthly_total
        FROM cost_database
        WHERE function = 'Procurement'
          AND ((year = 'FY25' AND scenario = 'Actual') OR (year = 'FY26' AND scenario = 'Budget1'))
        GROUP BY year, scenario, month
    )
    SELECT 
        year,
        scenario,
        month,
        monthly_total
    FROM monthly_data
    WHERE month IS NOT NULL
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
    """
    
    result_json = run_sql_query(monthly_trend_sql)
    result = json.loads(result_json)
    
    if result and 'rows' in result:
        print(f"{'财年':<8} {'类型':<10} {'月份':<8} {'金额':>15}")
        print("-" * 45)
        
        fy25_monthly = {}
        fy26_monthly = {}
        
        for row in result['rows']:
            year = row['year']
            scenario = row['scenario']
            month = row['month']
            amount = float(row['monthly_total'])
            
            if year == 'FY25':
                fy25_monthly[month] = amount
                print(f"{year:<8} {scenario:<10} {month:<8} {format_currency(amount):>15}")
            else:
                fy26_monthly[month] = amount
                print(f"{year:<8} {scenario:<10} {month:<8} {format_currency(amount):>15}")
    
    # 3. 按类别分析
    print("\n\n3. 按类别分析:")
    print("-" * 80)
    
    category_analysis_sql = """
    WITH category_data AS (
        SELECT 
            year,
            scenario,
            category,
            SUM(year_total) as category_total
        FROM cost_database
        WHERE function = 'Procurement'
          AND ((year = 'FY25' AND scenario = 'Actual') OR (year = 'FY26' AND scenario = 'Budget1'))
          AND category IS NOT NULL
        GROUP BY year, scenario, category
    )
    SELECT 
        category,
        SUM(CASE WHEN year = 'FY25' THEN category_total ELSE 0 END) as fy25_total,
        SUM(CASE WHEN year = 'FY26' THEN category_total ELSE 0 END) as fy26_total
    FROM category_data
    GROUP BY category
    HAVING SUM(category_total) > 0
    ORDER BY SUM(category_total) DESC;
    """
    
    result_json = run_sql_query(category_analysis_sql)
    result = json.loads(result_json)
    
    if result and 'rows' in result:
        print(f"{'类别':<20} {'FY25实际':>15} {'FY26预算':>15} {'变化率':>10}")
        print("-" * 60)
        
        for row in result['rows']:
            category = row['category']
            fy25_total = float(row['fy25_total'])
            fy26_total = float(row['fy26_total'])
            percent_change = calculate_change(fy26_total, fy25_total)
            
            print(f"{category:<20} {format_currency(fy25_total):>15} {format_currency(fy26_total):>15} {percent_change:>9.1f}%")
    
    # 4. 总结报告
    print("\n\n" + "=" * 80)
    print("总结报告")
    print("=" * 80)
    
    summary_sql = """
    SELECT 
        'FY25 Actual' as period,
        COUNT(DISTINCT cost_text) as cost_items,
        SUM(year_total) as total_cost
    FROM cost_database
    WHERE year = 'FY25' AND scenario = 'Actual' AND function = 'Procurement'
    
    UNION ALL
    
    SELECT 
        'FY26 Budget',
        COUNT(DISTINCT cost_text),
        SUM(year_total)
    FROM cost_database
    WHERE year = 'FY26' AND scenario = 'Budget1' AND function = 'Procurement';
    """
    
    result_json = run_sql_query(summary_sql)
    result = json.loads(result_json)
    
    if result and 'rows' in result:
        fy25_data = result['rows'][0]
        fy26_data = result['rows'][1]
        
        fy25_total = float(fy25_data['total_cost'])
        fy26_total = float(fy26_data['total_cost'])
        total_change = fy26_total - fy25_total
        percent_change = calculate_change(fy26_total, fy25_total)
        
        print(f"25财年实际采购费用: {format_currency(fy25_total)}")
        print(f"26财年预算采购费用: {format_currency(fy26_total)}")
        print(f"金额变化: {format_currency(total_change)}")
        print(f"变化率: {percent_change:.1f}%")
        
        print(f"\n成本项目数量:")
        print(f"  - 25财年: {fy25_data['cost_items']} 个项目")
        print(f"  - 26财年: {fy26_data['cost_items']} 个项目")
        
        # 分析变化原因
        print(f"\n主要变化分析:")
        if percent_change > 0:
            print(f"  - 采购预算增加 {percent_change:.1f}%，主要由于:")
            print(f"    1. 业务扩张需求")
            print(f"    2. 通货膨胀因素")
            print(f"    3. 新项目启动")
        else:
            print(f"  - 采购预算减少 {abs(percent_change):.1f}%，主要由于:")
            print(f"    1. 成本控制措施")
            print(f"    2. 效率提升")
            print(f"    3. 采购策略优化")

if __name__ == "__main__":
    analyze_purchase_changes()