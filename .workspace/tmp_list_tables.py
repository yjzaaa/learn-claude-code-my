from skills.finance.scripts.sql_query import run_sql_query
sql = """
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_type='BASE TABLE'
  AND (table_name LIKE '%cost%' OR table_name LIKE '%rate%' OR table_name LIKE '%mapping%')
ORDER BY table_schema, table_name;
"""
print(run_sql_query(sql))
