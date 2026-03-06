from skills.finance.scripts.dynamic_skill_sql import analyze_intent, construct_sql, execute_sql

# 用户问题和过滤条件
user_query = "25财年实际分摊给CT的IT费用是多少？"
user_filters = {"Year": "2025", "Scenario": "Actual", "[Function]": "IT Allocation", "[Key]": "CT"}

# 分析意图
intent_result = analyze_intent(user_query)
if intent_result["is_data_query"]:
    # 构造 SQL 查询
    sql_query = construct_sql(intent_result, user_filters)
    if sql_query:
        # 执行 SQL 查询
        results = execute_sql(sql_query)
        print("查询结果:", results)
    else:
        print("无法生成 SQL 查询！")
else:
    print("问题不涉及数据查询。")