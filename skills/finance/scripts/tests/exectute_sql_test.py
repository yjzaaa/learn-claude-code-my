from pathlib import Path
import sys
import logging

# 添加 scripts 目录到模块搜索路径
_scripts_dir = Path(__file__).resolve().parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from dynamic_skill_sql import execute_sql

def test_execute_sql():

    # 模拟用户查询和意图分析结果

    sql = """SELECT *
FROM cost_database
where  [Function] = 'IT'"""
    # 执行 SQL 查询
    sql_query = execute_sql(sql)
    print("生成的 SQL 查询:")
    print(sql_query)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_execute_sql()
