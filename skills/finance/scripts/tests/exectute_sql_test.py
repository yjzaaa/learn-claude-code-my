from pathlib import Path
import sys
import logging

sys.path.append(str(Path(__file__).resolve().parents[4]))

from skills.finance.scripts.dynamic_skill_sql import execute_sql

def test_execute_sql():

    # 模拟用户查询和意图分析结果
    
    sql = """SELECT * 
FROM SSME_FI_InsightBot_CostDataBase
where  [Function] = 'IT'"""
    # 执行 SQL 查询
    sql_query = execute_sql(sql)
    print("生成的 SQL 查询:")
    print(sql_query)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_execute_sql()