from skills.finance.scripts.generate_alloc_sql import generate_alloc_sql

# 定义查询参数
params = {
    "year": "FY25",
    "scenario": "Actual",
    "function": "IT Allocation",
    "key": "CT"
}

# 生成 SQL 查询
sql_query = generate_alloc_sql(params)

print(sql_query)