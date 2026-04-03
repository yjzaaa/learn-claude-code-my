#!/usr/bin/env python3
"""
执行FY25实际分摊给CT的IT费用查询
"""

import subprocess
import sys
import os

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
    FROM SSME_FI_InsightBot_CostDataBase cdb
    LEFT JOIN SSME_FI_InsightBot_Rate t7
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

def execute_sql():
    """执行SQL查询"""
    print("执行SQL查询：FY25实际分摊给CT的IT费用")
    print("=" * 60)
    
    # 将SQL写入临时文件
    temp_sql_file = "temp_query.sql"
    with open(temp_sql_file, "w", encoding="utf-8") as f:
        f.write(sql_query)
    
    try:
        # 根据技能文档，应该使用sql_query.py来执行
        # 但由于环境限制，这里模拟执行过程
        print("SQL查询已生成，需要连接到数据库执行")
        print("\n查询逻辑说明：")
        print("1. 按月计算分摊金额：基础金额 × 分摊比例")
        print("2. 按年汇总分摊金额")
        print("3. 返回FY25年的分摊总金额")
        print("\n查询条件：")
        print("- 年份：FY25")
        print("- 场景：Actual（实际）")
        print("- Function：IT Allocation（IT分摊）")
        print("- 分摊维度：业务线(BL) = 'CT'")
        print("- 分摊标准：使用对应的Key（IT Allocation对应480056 Cycle）")
        print("\n由于无法直接连接数据库，无法获取具体金额。")
        print("在实际环境中，应使用以下命令执行：")
        print(f'python sql_query.py --sql "{sql_query[:100]}..."')
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_sql_file):
            os.remove(temp_sql_file)

if __name__ == "__main__":
    execute_sql()