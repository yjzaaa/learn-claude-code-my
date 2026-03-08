import os
import sys

# 添加当前目录到路径
sys.path.append('.')

# 设置环境变量（如果.env文件存在）
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

print("Environment variables:")
print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_NAME: {os.getenv('DB_NAME')}")
print(f"DB_USER: {os.getenv('DB_USER')}")
print(f"DB_PASSWORD: {'*' * len(os.getenv('DB_PASSWORD', ''))}")
print(f"DB_PORT: {os.getenv('DB_PORT')}")

# 测试数据库连接
try:
    from skills.finance.scripts.sql_query import run_sql_query
    
    # 测试查询表结构
    sql = "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'cost_database' AND table_schema = 'public' ORDER BY ordinal_position;"
    result = run_sql_query(sql)
    print(f"\nQuery result: {result}")
    
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()