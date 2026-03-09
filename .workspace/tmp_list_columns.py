from skills.finance.scripts.sql_query import run_sql_query
sql = """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema='dbo' AND table_name='SSME_FI_InsightBot_CostDataBase'
ORDER BY ordinal_position;
"""
print(run_sql_query(sql))
