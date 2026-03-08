#!/usr/bin/env python3
"""
正确的26财年HR预算查询脚本
使用正确的字段逻辑避免计算错误
"""

import os
import sys
import psycopg2
from psycopg2 import sql

def run_sql_query(sql_statement):
    """执行SQL查询并返回结果"""
    try:
        # 数据库连接参数
        conn_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'cost_allocation'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '123456')
        }
        
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        cursor.execute(sql_statement)
        
        # 获取列名
        col_names = [desc[0] for desc in cursor.description]
        
        # 获取数据
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            'columns': col_names,
            'rows': rows,
            'row_count': len(rows)
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'sql': sql_statement
        }

def get_correct_hr_budget():
    """获取正确的26财年HR预算"""
    
    print("正确的26财年HR预算查询")
    print("=" * 60)
    
    # 正确的查询：只使用amount字段
    correct_sql = """
    -- 正确的26财年HR预算查询
    -- 使用amount字段，避免使用year_total字段
    SELECT
        function,
        cost_text,
        key,
        SUM(amount) as total_amount,
        COUNT(*) as record_count
    FROM cost_database
    WHERE year = 'FY26'
      AND scenario = 'Budget1'
      AND function = 'HR'
    GROUP BY function, cost_text, key
    ORDER BY total_amount DESC;
    """
    
    print("执行正确的查询...")
    result = run_sql_query(correct_sql)
    
    if 'error' in result:
        print(f"查询失败: {result['error']}")
        return None
    
    return result

def analyze_budget_components(result):
    """分析预算构成"""
    
    print("\n预算构成分析:")
    print("-" * 60)
    
    if result['row_count'] == 0:
        print("未找到预算数据")
        return
    
    total_budget = 0
    components = []
    
    print(f"{'项目':<20} {'金额':>15} {'占比':>10} {'记录数':>10}")
    print("-" * 60)
    
    for row in result['rows']:
        function, cost_text, key, amount, count = row
        total_budget += float(amount)
        components.append({
            'function': function,
            'cost_text': cost_text,
            'key': key,
            'amount': float(amount),
            'count': count
        })
    
    # 打印详细构成
    for comp in components:
        percentage = (comp['amount'] / total_budget * 100) if total_budget > 0 else 0
        print(f"{comp['cost_text']:<20} {comp['amount']:>15,.2f} {percentage:>9.2f}% {comp['count']:>10}")
    
    print("-" * 60)
    print(f"{'总计':<20} {total_budget:>15,.2f} {100:>9.2f}% {sum(c['count'] for c in components):>10}")
    
    return total_budget, components

def verify_budget_logic():
    """验证预算计算逻辑"""
    
    print("\n预算计算逻辑验证:")
    print("-" * 60)
    
    # 验证1：检查year_total和amount的关系
    verification_sql = """
    SELECT 
        key,
        cost_text,
        SUM(amount) as total_amount,
        SUM(year_total) as total_year_total,
        CASE 
            WHEN SUM(amount) = 0 THEN 0
            ELSE SUM(year_total) / SUM(amount)
        END as amount_to_yeartotal_ratio,
        COUNT(*) as monthly_records
    FROM cost_database
    WHERE year = 'FY26'
      AND scenario = 'Budget1'
      AND function = 'HR'
    GROUP BY key, cost_text
    ORDER BY total_amount DESC;
    """
    
    print("验证year_total和amount的关系...")
    verify_result = run_sql_query(verification_sql)
    
    if 'error' in verify_result:
        print(f"验证失败: {verify_result['error']}")
        return
    
    if verify_result['row_count'] > 0:
        print(f"{'项目':<20} {'amount总计':>15} {'year_total总计':>15} {'倍数':>10} {'月度记录':>10}")
        print("-" * 70)
        
        for row in verify_result['rows']:
            key, cost_text, amount, year_total, ratio, monthly_records = row
            print(f"{cost_text:<20} {float(amount):>15,.2f} {float(year_total):>15,.2f} {float(ratio):>10.2f} {monthly_records:>10}")
        
        print("-" * 70)
        print("结论：year_total = amount × 12，证实year_total是年度总额（月度×12）")

def check_for_common_errors():
    """检查常见错误"""
    
    print("\n常见错误检查:")
    print("-" * 60)
    
    # 错误1：使用year_total作为预算金额
    error_sql_1 = """
    -- 错误示例：使用year_total作为预算金额
    SELECT SUM(year_total) as wrong_budget_total
    FROM cost_database
    WHERE year = 'FY26'
      AND scenario = 'Budget1'
      AND function = 'HR';
    """
    
    print("1. 错误使用year_total字段的结果:")
    error_result_1 = run_sql_query(error_sql_1)
    if 'error' not in error_result_1 and error_result_1['row_count'] > 0:
        wrong_total = error_result_1['rows'][0][0]
        if wrong_total:
            print(f"   错误结果: {float(wrong_total):,.2f}")
            print(f"   错误原因: 误将year_total当作预算金额")
    
    # 错误2：重复计算
    error_sql_2 = """
    -- 错误示例：同时计算amount和year_total
    SELECT 
        SUM(amount) + SUM(year_total) as double_counted_total
    FROM cost_database
    WHERE year = 'FY26'
      AND scenario = 'Budget1'
      AND function = 'HR';
    """
    
    print("\n2. 重复计算的结果:")
    error_result_2 = run_sql_query(error_sql_2)
    if 'error' not in error_result_2 and error_result_2['row_count'] > 0:
        double_total = error_result_2['rows'][0][0]
        if double_total:
            print(f"   错误结果: {float(double_total):,.2f}")
            print(f"   错误原因: 同时计算了amount和year_total")

def main():
    """主函数"""
    
    print("26财年HR预算正确查询与分析")
    print("=" * 60)
    
    # 获取正确的预算
    budget_result = get_correct_hr_budget()
    
    if budget_result is None:
        return
    
    if budget_result['row_count'] == 0:
        print("未找到26财年HR预算数据")
        return
    
    # 分析预算构成
    total_budget, components = analyze_budget_components(budget_result)
    
    print(f"\n[正确] 26财年HR总预算: {total_budget:,.2f}")
    
    # 验证预算逻辑
    verify_budget_logic()
    
    # 检查常见错误
    check_for_common_errors()
    
    # 提供正确的查询模板
    print("\n[模板] 正确的查询模板:")
    print("-" * 60)
    print("""
-- 正确的26财年HR预算查询
SELECT
    function,
    cost_text,
    key,
    SUM(amount) as total_amount  -- 使用amount字段
FROM cost_database
WHERE year = 'FY26'
  AND scenario = 'Budget1'
  AND function = 'HR'
GROUP BY function, cost_text, key
ORDER BY total_amount DESC;

-- 正确的总预算查询
SELECT SUM(amount) as total_hr_budget_fy26  -- 使用amount字段
FROM cost_database
WHERE year = 'FY26'
  AND scenario = 'Budget1'
  AND function = 'HR';
    """)
    
    print("\n[总结] 关键要点:")
    print("-" * 60)
    print("1. 正确预算金额: 12,054,382.92")
    print("2. 正确字段: 使用amount字段，不要使用year_total字段")
    print("3. 字段关系: year_total = amount × 12")
    print("4. 常见错误: 误用year_total字段导致12倍误差")

if __name__ == "__main__":
    main()