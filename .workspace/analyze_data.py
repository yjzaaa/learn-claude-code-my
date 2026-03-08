import sys
sys.path.append('skills/finance/scripts')
from sql_query import run_sql_query
import json

# 查看所有不同的function
print("所有不同的function:")
result = run_sql_query("SELECT DISTINCT function FROM cost_database ORDER BY function")
data = json.loads(result)
for row in data['rows']:
    print(f"  - {row['function']}")

print("\n所有不同的cost_text:")
result = run_sql_query("SELECT DISTINCT cost_text FROM cost_database ORDER BY cost_text")
data = json.loads(result)
for row in data['rows']:
    print(f"  - {row['cost_text']}")

print("\n所有不同的scenario:")
result = run_sql_query("SELECT DISTINCT scenario FROM cost_database ORDER BY scenario")
data = json.loads(result)
for row in data['rows']:
    print(f"  - {row['scenario']}")

print("\n所有不同的year:")
result = run_sql_query("SELECT DISTINCT year FROM cost_database ORDER BY year")
data = json.loads(result)
for row in data['rows']:
    print(f"  - {row['year']}")