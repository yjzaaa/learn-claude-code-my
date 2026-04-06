#!/usr/bin/env python3
"""
简单执行FY25实际分摊给CT的IT费用查询
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

def main():
    print("FY25实际分摊给CT的IT费用查询")
    print("=" * 60)
    
    # 切换到scripts目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("数据库连接配置:")
    print("- 主机: localhost")
    print("- 端口: 5432")
    print("- 数据库: cost_allocation")
    print("- 用户名: postgres")
    print("- 密码: 123456")
    print()
    
    # 先测试连接
    print("1. 测试数据库连接...")
    test_cmd = ['python', 'sql_query.py', '--sql', 'SELECT 1 as test_value']
    
    try:
        test_result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10
        )
        
        if test_result.returncode != 0:
            print("[失败] 数据库连接测试失败")
            print(f"错误信息: {test_result.stderr}")
            print("\n可能的原因:")
            print("1. PostgreSQL数据库没有运行")
            print("2. 数据库配置不正确")
            print("3. 缺少Python数据库驱动")
            print("\n建议:")
            print("1. 检查PostgreSQL服务是否启动")
            print("2. 确认数据库cost_allocation是否存在")
            print("3. 安装psycopg2: pip install psycopg2-binary")
            return
        
        print("[成功] 数据库连接正常")
        
    except Exception as e:
        print(f"[错误] 连接测试异常: {e}")
        return
    
    # 执行主查询
    print("\n2. 执行FY25 IT费用分摊查询...")
    main_cmd = ['python', 'sql_query.py', '--sql', sql_query]
    
    try:
        result = subprocess.run(
            main_cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )
        
        print(f"返回码: {result.returncode}")
        
        if result.returncode == 0:
            print("[成功] 查询执行完成")
            print("\n查询结果:")
            print("-" * 40)
            
            # 尝试解析结果
            try:
                data = json.loads(result.stdout)
                if "rows" in data:
                    rows = data["rows"]
                    if rows:
                        for row in rows:
                            year = row.get(year, "未知")
                            amount = row.get("Year_Allocated_Cost", 0)
                            
                            print(f"财年: FY{year}")
                            print(f"分摊给CT的IT费用: {amount}")
                            
                            # 尝试格式化金额
                            try:
                                amount_float = float(amount)
                                if amount_float == 0:
                                    print("金额: 0.00")
                                elif amount_float > 0:
                                    print(f"金额: {amount_float:,.2f}")
                                else:
                                    print(f"金额: ({abs(amount_float):,.2f})")  # 负值表示成本分摊
                            except:
                                print(f"金额: {amount}")
                    else:
                        print("没有找到匹配的数据")
                        print("\n可能的原因:")
                        print("1. 数据库中不存在FY25 Actual的数据")
                        print("2. 没有IT Allocation到CT的分摊记录")
                        print("3. 业务线CT的值可能不是'CT'")
                        print("4. 表名或字段名可能不同")
                else:
                    print(f"原始返回: {result.stdout}")
            except json.JSONDecodeError:
                print(f"原始返回: {result.stdout}")
        else:
            print("[失败] 查询执行错误")
            print(f"错误输出: {result.stderr}")
            print(f"标准输出: {result.stdout}")
            
    except subprocess.TimeoutExpired:
        print("[超时] 查询执行超时")
    except Exception as e:
        print(f"[异常] 查询执行异常: {e}")
    
    print("\n" + "=" * 60)
    print("查询完成")

if __name__ == "__main__":
    main()