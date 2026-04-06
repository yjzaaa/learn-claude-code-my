#!/usr/bin/env python3
"""
FY25实际分摊给CT的IT费用查询结果报告
"""

import json
import subprocess
import os

def execute_query():
    """执行查询并返回结果"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    sql = """WITH monthly_alloc AS (
    SELECT
        cdb.year,
        COALESCE(SUM(cdb.amount::float), 0) AS base_month_cost,
        COALESCE(
            SUM(
                cdb.amount::float * 
                COALESCE(
                    CASE 
                        WHEN t7.rate_no::float > 1 
                        THEN t7.rate_no::float / 100
                        ELSE t7.rate_no::float
                    END, 
                    0
                )
            ), 
            0
        ) AS allocated_month_cost
    FROM cost_database cdb
    LEFT JOIN rate_table t7
        ON cdb.year = t7.year
        AND cdb.scenario = t7.scenario
        AND cdb.key = t7.key
        AND cdb.month = t7.month
    WHERE cdb.year = 'FY25'
        AND cdb.scenario = 'Actual'
        AND cdb.function = 'IT Allocation'
        AND t7.bl = 'CT'
    GROUP BY cdb.year
),
yearly_agg AS (
    SELECT
        year,
        SUM(allocated_month_cost) AS year_allocated_cost
    FROM monthly_alloc
    GROUP BY year
)
SELECT
    year,
    year_allocated_cost
FROM yearly_agg
WHERE year = 'FY25';"""
    
    cmd = ['python', 'sql_query.py', '--sql', sql]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": result.stderr}
            
    except Exception as e:
        return {"error": str(e)}

def format_report(data):
    """格式化报告"""
    print("=" * 70)
    print("            FY25实际分摊给CT的IT费用查询报告")
    print("=" * 70)
    
    if "error" in data:
        print(f"\n❌ 查询错误: {data['error']}")
        return
    
    if "rows" not in data or not data["rows"]:
        print("\n⚠️  查询成功，但没有找到匹配的数据")
        print("\n可能的原因:")
        print("1. 数据库中不存在FY25 Actual的IT Allocation数据")
        print("2. 没有分摊到业务线CT的记录")
        print("3. 业务线CT的值可能不是'CT'")
        return
    
    row = data["rows"][0]
    year = row.get(year, "FY25")
    amount = row.get("year_allocated_cost", 0)
    
    print(f"\n📊 查询结果:")
    print(f"   财年: {year}")
    print(f"   分摊对象: CT (业务线)")
    print(f"   费用类型: IT Allocation (IT分摊)")
    print(f"   数据场景: Actual (实际)")
    
    print(f"\n💰 分摊金额:")
    try:
        amount_float = float(amount)
        if amount_float == 0:
            print(f"   ¥ 0.00")
            print(f"   (零值，可能表示没有分摊或分摊金额为零)")
        elif amount_float < 0:
            # 负值表示成本分摊
            abs_amount = abs(amount_float)
            print(f"   ¥ ({abs_amount:,.2f})")
            print(f"   (负值表示成本分摊，实际分摊金额为 {abs_amount:,.2f})")
        else:
            print(f"   ¥ {amount_float:,.2f}")
    except:
        print(f"   {amount}")
    
    print(f"\n📈 业务说明:")
    print("   1. 此金额为FY25财年实际发生的IT费用分摊")
    print("   2. 分摊对象为业务线CT")
    print("   3. 计算方式: 按月计算分摊金额后年度汇总")
    print("   4. 分摊标准: IT Allocation对应Key '480056 Cycle'")
    
    print(f"\n🔍 查询详情:")
    print("   - 数据库: cost_allocation (PostgreSQL)")
    print("   - 主表: cost_database")
    print("   - 分摊规则表: rate_table")
    print("   - 关联条件: 年、场景、Key、月四重关联")
    
    print(f"\n" + "=" * 70)
    print("报告生成完成")

def main():
    print("正在查询FY25实际分摊给CT的IT费用...")
    print("-" * 50)
    
    data = execute_query()
    format_report(data)

if __name__ == "__main__":
    main()