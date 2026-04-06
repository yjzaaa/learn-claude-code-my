import argparse
import sys
from pathlib import Path

# 添加当前目录到模块搜索路径
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from sql_query import run_sql_query


def _default_sql() -> str:
    """Return canonical FY26 HR budget sample query."""
    return """
    SELECT SUM([Amount]) AS total_budget
    FROM dbo.SSME_FI_InsightBot_CostDataBase
    WHERE [Year] = 'FY26'
      AND [Scenario] = 'Budget1'
      AND [Function] = 'HR';
    """


def main() -> None:
    """Run a provided SQL statement, or fallback to canonical sample SQL."""
    parser = argparse.ArgumentParser(description="Run finance SQL via helper script.")
    parser.add_argument("--sql", dest="sql", help="SQL statement to execute")
    args = parser.parse_args()

    sql = args.sql.strip() if args.sql else _default_sql()
    result = run_sql_query(sql)
    print(result)

if __name__ == "__main__":
    main()
