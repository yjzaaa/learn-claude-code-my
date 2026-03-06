from skills.finance.scripts.sql_query import run_sql_query

def test_finance_query():
    with open('finance_query.sql', 'r') as file:
        sql = file.read()
    result = run_sql_query(sql)
    print(result)

if __name__ == "__main__":
    test_finance_query()