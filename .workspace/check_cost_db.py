import sys
sys.path.append('skills/finance/scripts')
from sql_query import run_sql_query

# 查看cost_database表结构
result = run_sql_query("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'cost_database'
    ORDER BY ordinal_position
""")
print("cost_database表结构:")
print(result)

# 查看表的前几行数据
print("\ncost_database表前10行数据:")
result2 = run_sql_query("SELECT * FROM cost_database LIMIT 10")
print(result2)