import json

try:
    from skills.finance.scripts.sql_query import run_sql_query
except ImportError:
    from sql_query import run_sql_query

def analyze_intent(user_query: str):
    """
    分析用户问题意图。
    返回数据库查询相关的意图及目标表。
    自动添加默认场景过滤条件（如 Scenario = 'Budget1'）。
    """
    keywords = {
        "分摊": "SSME_FI_InsightBot_CostDataBase",
        "预算": "SSME_FI_InsightBot_CostDataBase",
        "趋势": "SSME_FI_InsightBot_CostDataBase"
    }

    for keyword, table in keywords.items():
        # 默认场景过滤条件
        default_scenario = "Budget1"
        if keyword in user_query:
            return {
                "scenario": default_scenario,
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
        filter_conditions = " AND ".join([f"[{k}] = '{v}'" for k, v in user_filters.items()]) + f" AND [Scenario] = '{intent_result.get('scenario')}'"
        return f"{base_query} WHERE {filter_conditions};"

    return base_query

def execute_sql(sql_query):
    """
    执行 SQL 查询
    """
    import decimal
    def decimal_default(obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        raise TypeError
    result = run_sql_query(sql_query)
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, default=decimal_default)

if __name__ == "__main__":
    user_query = "IT费用都有哪些服务，这些服务是按什么分摊给业务部门的？"
    user_filters = {"Function": "IT", "Scenario": "Budget1"}

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