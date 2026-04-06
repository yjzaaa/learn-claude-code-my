#!/usr/bin/env python3
"""
直接执行FY25实际分摊给CT的IT费用查询
"""

import subprocess
import sys
import os
import json

# 生成的SQL查询
sql_query = """WITH monthly_alloc AS (
    SELECT
        cdb.[Year],
        COALESCE(SUM(CAST(cdb.[Amount] AS FLOAT)), 0) AS [Base_Month_Cost],
        COALESCE(
            SUM(
                CAST(cdb.[Amount] AS FLOAT) * 
                COALESCE(
                    CASE 
                        WHEN TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT) > 1 
                        THEN TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT) / 100
                        ELSE TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT)
                    END, 
                    0
                )
            ), 
            0
        ) AS [Allocated_Month_Cost]
    FROM cost_database cdb
    LEFT JOIN rate_table t7
        ON cdb.[Year] = t7.[Year]
        AND cdb.[Scenario] = t7.[Scenario]
        AND cdb.[Key] = t7.[Key]
        AND cdb.[Month] = t7.[Month]
    WHERE cdb.year = 'FY25'
        AND cdb.scenario = 'Actual'
        AND cdb.[Function] = 'IT Allocation'
        AND t7.[BL] = 'CT'
    GROUP BY cdb.Year
),
yearly_agg AS (
    SELECT
        [Year],
        SUM([Allocated_Month_Cost]) AS [Year_Allocated_Cost]
    FROM monthly_alloc
    GROUP BY [Year]
)
SELECT
    [Year],
    [Year_Allocated_Cost]
FROM yearly_agg
WHERE year = 'FY25';"""

def execute_with_sql_query():
    """使用sql_query.py执行查询"""
    print("正在执行查询：FY25实际分摊给CT的IT费用")
    print("=" * 60)
    
    # 切换到scripts目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 构建命令
    cmd = ['python', 'sql_query.py', '--sql', sql_query]
    
    print(f"执行命令: {' '.join(cmd[:3])} [SQL内容已隐藏]")
    print("\n数据库连接配置:")
    print(f"- 主机: localhost (默认)")
    print(f"- 端口: 5432 (默认)")
    print(f"- 数据库: cost_allocation (默认)")
    print(f"- 用户名: postgres (默认)")
    print(f"- 密码: 123456 (默认)")
    print("\n正在尝试连接数据库...")
    
    try:
        # 执行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )
        
        print("\n执行结果:")
        print("-" * 40)
        
        if result.returncode == 0:
            # 尝试解析JSON结果
            try:
                data = json.loads(result.stdout)
                if "rows" in data:
                    rows = data["rows"]
                    if rows:
                        print(f"查询成功！找到 {len(rows)} 条记录:")
                        for row in rows:
                            year = row.get(year, "未知")
                            amount = row.get("Year_Allocated_Cost", 0)
                            print(f"\nFY{year} 实际分摊给CT的IT费用: {amount}")
                            
                            # 格式化金额显示
                            try:
                                amount_num = float(amount)
                                if amount_num >= 0:
                                    print(f"  金额: {amount_num:,.2f}")
                                else:
                                    print(f"  金额: ({abs(amount_num):,.2f})")  # 负值表示分摊成本
                            except:
                                print(f"  金额: {amount}")
                    else:
                        print("查询成功，但没有找到匹配的数据。")
                        print("可能的原因:")
                        print("1. 数据库中不存在FY25 Actual的数据")
                        print("2. 没有IT Allocation到CT的分摊记录")
                        print("3. 业务线CT的值可能不是'CT'，需要确认具体值")
                else:
                    print(f"返回结果: {result.stdout}")
            except json.JSONDecodeError:
                # 如果不是JSON，直接显示输出
                print(result.stdout)
        else:
            print(f"执行失败 (返回码: {result.returncode})")
            print(f"错误输出: {result.stderr}")
            print(f"标准输出: {result.stdout}")
            
            # 常见错误分析
            if "Connection refused" in result.stderr or "无法连接到服务器" in result.stderr:
                print("\n❌ 数据库连接失败！")
                print("可能的原因:")
                print("1. PostgreSQL数据库没有运行")
                print("2. 数据库不在localhost:5432")
                print("3. 用户名/密码错误")
                print("\n建议检查:")
                print("1. 运行: sudo systemctl status postgresql")
                print("2. 检查PostgreSQL是否监听5432端口")
                print("3. 验证数据库cost_allocation是否存在")
                
    except subprocess.TimeoutExpired:
        print("❌ 查询超时！数据库可能没有响应。")
    except Exception as e:
        print(f"❌ 执行过程中发生错误: {e}")

def check_database_connection():
    """检查数据库连接"""
    print("\n" + "=" * 60)
    print("数据库连接检查")
    print("=" * 60)
    
    # 尝试简单的连接测试
    test_sql = "SELECT 1 as test_value, current_date as current_date"
    cmd = ['python', 'sql_query.py', '--sql', test_sql]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ 数据库连接测试成功！")
            try:
                data = json.loads(result.stdout)
                if "rows" in data and data["rows"]:
                    print(f"  测试查询返回: {data['rows'][0]}")
            except:
                pass
        else:
            print("❌ 数据库连接测试失败")
            print(f"  错误: {result.stderr[:200]}")
            
    except Exception as e:
        print(f"❌ 连接测试异常: {e}")

if __name__ == "__main__":
    print("FY25实际分摊给CT的IT费用查询")
    print("=" * 60)
    
    # 先检查数据库连接
    check_database_connection()
    
    # 执行主查询
    execute_with_sql_query()
    
    print("\n" + "=" * 60)
    print("查询完成")
    print("=" * 60)