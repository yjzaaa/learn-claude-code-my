import os
import sys

# 设置数据库连接参数
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'cost_allocation'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = '123456'
os.environ['DB_PORT'] = '5432'

# 添加技能脚本路径
sys.path.append('skills/finance/scripts')

try:
    from sql_query import run_sql_query
    
    # 查询表结构
    sql = '''
    SELECT
        column_name,
        data_type,
        is_nullable
    FROM information_schema.columns
    WHERE table_name = 'cost_database'
      AND table_schema = 'public'
    ORDER BY ordinal_position;
    '''
    
    result = run_sql_query(sql)
    print("表结构查询结果:")
    print(result)
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()