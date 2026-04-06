import json
import pyodbc  # 执行 SQL 查询的标准库，需确保已安装

def analyze_intent(user_query: str):
    """
    分析用户问题意图。
    返回数据库查询相关的意图及目标表。
    自动添加默认场景过滤条件（如 Scenario = 'Budget1'）。
    """
    keywords = {
        "分摊": "cost_database",
        "预算": "cost_database",
        "趋势": "cost_database"
    }

    for keyword, table in keywords.items():
        # 默认场景过滤条件
        default_scenario = "Budget1"
        if keyword in user_query:
            return {
                scenario: default_scenario,
                "is_data_query": True,
                "table": table,
                "reason": f"关键词匹配: {keyword}"
            }
    return {
        "is_data_query": False,
        "reason": "未匹配到关键词"
    }

def construct_sql(intent_result, user_filters):
    """
    根据分析结果和用户过滤条件生成 SQL。
    """
    table = intent_result.get("table")
    if not table:
        return None

    base_query = f"SELECT * FROM {table}"
    if user_filters:
        filter_conditions = " AND ".join([f"{k} = '{v}'" for k, v in user_filters.items()]) + f" AND Scenario = '{intent_result.get('scenario')}'"
        return f"{base_query} WHERE {filter_conditions};"

    return base_query

def execute_sql(sql_query):
    """
    执行 SQL 查询
    """
    conn_str = (
        "Driver={SQL Server};"
        "Server=Shai438a.ad005.onehc.net,1433;"
        "Database=SmartMES_Demo;"
        "Uid=testlogin;"
        "Pwd=WIN@superman7119;"
    )

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(sql_query)

        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()
        return results
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    user_query = "白领数分摊服务有哪些？"
    user_filters = {year: "2026", scenario: "Budget1"}

    intent_result = analyze_intent(user_query)
    if intent_result["is_data_query"]:
        sql_query = construct_sql(intent_result, user_filters)
        if sql_query:
            results = execute_sql(sql_query)
            print(json.dumps(results, ensure_ascii=False, indent=4))
        else:
            print("无法生成 SQL 查询！")
    else:
        print("问题不涉及数据查询。")