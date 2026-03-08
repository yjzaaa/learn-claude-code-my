import os
import sys

# 添加skills目录到路径
sys.path.append('skills/finance/scripts')

# 导入sql_query模块
try:
    from sql_query import run_sql_query
    print("Successfully imported sql_query module")
    
    # 测试简单的SQL查询
    test_sql = "SELECT 1 as test_value"
    print(f"\nTesting SQL query: {test_sql}")
    
    result = run_sql_query(test_sql)
    print(f"Result: {result}")
    
except Exception as e:
    print(f"Error: {e}")
    print("\nCurrent environment variables:")
    print(f"DB_HOST: {os.getenv('DB_HOST')}")
    print(f"DB_NAME: {os.getenv('DB_NAME')}")
    print(f"DB_USER: {os.getenv('DB_USER')}")
    print(f"DB_PASSWORD: {'*' * len(os.getenv('DB_PASSWORD', '')) if os.getenv('DB_PASSWORD') else 'Not set'}")
    print(f"DB_PORT: {os.getenv('DB_PORT')}")