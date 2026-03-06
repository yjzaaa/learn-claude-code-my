from skills.finance.scripts.sql_query import run_sql_query
import json

def query_table_structure():
    table_name = "SSME_FI_InsightBot_CostDataBase"

    schema_sql = (
        "SELECT COLUMN_NAME, DATA_TYPE "
        "FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_NAME = '{table_name}'"
    )

    sample_sql = f"SELECT TOP 5 ID, Year, Scenario, [Function], [Cost text], Account, Category, [Key], CAST([Year Total] AS FLOAT) AS [Year Total], Month, CAST(Amount AS FLOAT) AS Amount, CONVERT(VARCHAR, CreateTime, 120) AS CreateTime FROM {table_name}"

    import decimal
    import datetime

    def serialize(obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        raise TypeError("Type not serializable")

    schema_result = run_sql_query(schema_sql, limit=500)
    import decimal
    import datetime

    def serialize(obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        raise TypeError("Type not serializable")

    sample_result_raw = run_sql_query(sample_sql, limit=5)
    sample_result = sample_result_raw

    print("Schema Result:", schema_result)
    print("Sample Result:", sample_result)
    return json.dumps(
        {
            "schema": schema_result,
            "sample": sample_result
        },
        ensure_ascii=False
    )

if __name__ == "__main__":
    output = query_table_structure()
    print(output)