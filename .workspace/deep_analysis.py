#!/usr/bin/env python3
"""
深入分析26财年HR预算数据
"""

import os
import sys

def analyze_data_structure():
    """分析数据结构以理解可能的错误"""
    
    print("26财年HR预算深度分析")
    print("=" * 60)
    
    # 基于查询结果的分析
    print("\n1. 基于查询结果的分析:")
    print("-" * 40)
    
    # 原始查询结果
    query_results = [
        ("HR", "HR", "headcount", 10383000.00, 124596000.00),
        ("HR", "GBS H2R", "headcount", 1471239.96, 17654880.00),
        ("HR", "Field HR", "headcount", 200142.96, 2401716.00)
    ]
    
    print("查询到的原始数据:")
    for func, cost_text, key, amount, year_total in query_results:
        print(f"  {func} | {cost_text} | {key}:")
        print(f"    amount: {amount:,.2f}")
        print(f"    year_total: {year_total:,.2f}")
        print(f"    year_total / amount = {year_total/amount:.2f}")
    
    print("\n2. 数据关系分析:")
    print("-" * 40)
    
    # 分析year_total和amount的关系
    for func, cost_text, key, amount, year_total in query_results:
        ratio = year_total / amount
        print(f"\n{func} | {cost_text}:")
        print(f"  amount: {amount:,.2f}")
        print(f"  year_total: {year_total:,.2f}")
        print(f"  倍数关系: {ratio:.2f}倍")
        
        if abs(ratio - 12) < 0.1:
            print(f"  → year_total可能是amount的12倍（月度×12）")
        else:
            print(f"  → 非标准倍数关系，需要进一步调查")
    
    print("\n3. 汇总计算分析:")
    print("-" * 40)
    
    # 正确的汇总
    correct_total = sum(amount for _, _, _, amount, _ in query_results)
    print(f"正确的汇总（sum(amount)）: {correct_total:,.2f}")
    
    # 错误的汇总（可能的方式）
    wrong_total_1 = sum(year_total for _, _, _, _, year_total in query_results)
    print(f"错误的汇总1（sum(year_total)）: {wrong_total_1:,.2f}")
    
    # 检查是否有人错误地使用了year_total
    print(f"\n如果错误地使用year_total作为预算金额:")
    print(f"  错误金额: {wrong_total_1:,.2f}")
    print(f"  正确金额: {correct_total:,.2f}")
    print(f"  误差倍数: {wrong_total_1/correct_total:.2f}倍")
    
    print("\n4. 可能的错误场景:")
    print("-" * 40)
    
    scenarios = [
        {
            "name": "场景1：误用year_total字段",
            "description": "将year_total误认为是年度预算金额",
            "错误计算": wrong_total_1,
            "正确计算": correct_total,
            "误差": wrong_total_1 - correct_total
        },
        {
            "name": "场景2：重复计算",
            "description": "同时计算了amount和year_total",
            "错误计算": correct_total + wrong_total_1,
            "正确计算": correct_total,
            "误差": wrong_total_1
        },
        {
            "name": "场景3：单位误解",
            "description": "将月度数据当作年度数据",
            "错误计算": correct_total * 12,
            "正确计算": correct_total,
            "误差": correct_total * 11
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}:")
        print(f"   描述: {scenario['description']}")
        print(f"   错误结果: {scenario['错误计算']:,.2f}")
        print(f"   正确结果: {scenario['正确计算']:,.2f}")
        print(f"   误差: {scenario['误差']:,.2f}")
    
    print("\n5. 建议的验证查询:")
    print("-" * 40)
    
    validation_queries = [
        {
            "name": "查询1：验证数据完整性",
            "sql": """
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT key) as unique_keys,
                MIN(year_total) as min_year_total,
                MAX(year_total) as max_year_total,
                AVG(year_total) as avg_year_total
            FROM cost_database
            WHERE year = 'FY26'
              AND scenario = 'Budget1'
              AND function = 'HR';
            """
        },
        {
            "name": "查询2：检查月度数据",
            "sql": """
            SELECT 
                month,
                COUNT(*) as record_count,
                SUM(amount) as monthly_total,
                AVG(amount) as avg_monthly
            FROM cost_database
            WHERE year = 'FY26'
              AND scenario = 'Budget1'
              AND function = 'HR'
            GROUP BY month
            ORDER BY month;
            """
        },
        {
            "name": "查询3：理解year_total含义",
            "sql": """
            SELECT 
                key,
                cost_text,
                COUNT(*) as records,
                SUM(amount) as total_amount,
                SUM(year_total) as total_year_total,
                CASE 
                    WHEN SUM(amount) = 0 THEN 0
                    ELSE SUM(year_total) / SUM(amount)
                END as ratio
            FROM cost_database
            WHERE year = 'FY26'
              AND scenario = 'Budget1'
              AND function = 'HR'
            GROUP BY key, cost_text
            ORDER BY ratio DESC;
            """
        }
    ]
    
    for query in validation_queries:
        print(f"\n{query['name']}:")
        print(query['sql'])
    
    print("\n6. 结论:")
    print("-" * 40)
    print("最可能的错误原因：")
    print("1. 误将year_total字段当作年度预算金额")
    print("2. year_total可能是amount的12倍（月度×12）")
    print("3. 正确的预算金额应使用sum(amount)，结果为12,054,382.92")
    print("\n建议：")
    print("1. 明确year_total字段的业务含义")
    print("2. 在查询中只使用amount字段进行汇总")
    print("3. 建立数据字典，明确每个字段的含义")

if __name__ == "__main__":
    analyze_data_structure()