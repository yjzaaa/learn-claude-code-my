import sys
sys.path.append('skills/finance/scripts')
from sql_query import run_sql_query

# 查询所有表
result = run_sql_query("""
    SELECT table_name, table_type 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    ORDER BY table_name
""")
print(result)