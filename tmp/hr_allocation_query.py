
import psycopg2
import pandas as pd

# 数据库连接信息
db_config = {
    'host': 'localhost',
    'port': '5432',
    'database': 'cost_allocation',
    'user': 'postgres',
    'password': '123456'
}

# SQL 查询：比较 FY26 BGT 和 FY25 Actual 的 HR Allocation 在 Cost Center 4130011 下的变化
sql_query = """
WITH fy26_bgt AS (
    SELECT 
        SUM(amount) AS fy26_bgt_amount
    FROM cost_database
    WHERE function = 'HR Allocation'
      AND scenario = 'Budget1'
      AND year = 'FY26'
      AND cost_center = '4130011'
),
fy25_actual AS (
    SELECT 
        SUM(amount) AS fy25_actual_amount
    FROM cost_database
    WHERE function = 'HR Allocation'
      AND scenario = 'Actual'
      AND year = 'FY25'
      AND cost_center = '4130011'
)
SELECT 
    COALESCE(fy26_bgt.fy26_bgt_amount, 0) AS "FY26 BGT 总金额",
    COALESCE(fy25_actual.fy25_actual_amount, 0) AS "FY25 Actual 总金额",
    COALESCE(fy26_bgt.fy26_bgt_amount, 0) - COALESCE(fy25_actual.fy25_actual_amount, 0) AS "变化金额 (FY26 BGT - FY25 Actual)",
    CASE 
        WHEN COALESCE(fy25_actual.fy25_actual_amount, 0) = 0 THEN 0
        ELSE ROUND(
            (COALESCE(fy26_bgt.fy26_bgt_amount, 0) - COALESCE(fy25_actual.fy25_actual_amount, 0)) 
            / NULLIF(fy25_actual.fy25_actual_amount, 0) * 100, 
            2
        )
    END AS "变化百分比 (%)"
FROM fy26_bgt, fy25_actual;
"""

# 执行查询
try:
    conn = psycopg2.connect(**db_config)
    df = pd.read_sql(sql_query, conn)
    print("=" * 80)
    print("HR Allocation 在 Cost Center 4130011 下的 FY26 BGT vs FY25 Actual 对比")
    print("=" * 80)
    print()
    print(df.to_string(index=False))
    print()
    print("=" * 80)
    
    # 格式化输出结果
    fy26_bgt = df.iloc[0]['FY26 BGT 总金额']
    fy25_actual = df.iloc[0]['FY25 Actual 总金额']
    delta = df.iloc[0]['变化金额 (FY26 BGT - FY25 Actual)']
    change_pct = df.iloc[0]['变化百分比 (%)']
    
    print("\n📊 结果汇总:")
    print(f"  • FY26 BGT 总金额:    {fy26_bgt:,.2f}")
    print(f"  • FY25 Actual 总金额: {fy25_actual:,.2f}")
    print(f"  • 变化金额:           {delta:,.2f} ({'↑' if delta > 0 else '↓' if delta < 0 else '→'})")
    print(f"  • 变化百分比:         {change_pct}%")
    print("=" * 80)
    
except Exception as e:
    print(f"查询出错: {e}")
finally:
    if 'conn' in locals():
        conn.close()
