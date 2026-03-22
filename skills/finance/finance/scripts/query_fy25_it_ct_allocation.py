from allocation_utils import generate_alloc_sql

# 根据用户问题生成SQL
# 问题：25财年实际分摊给CT的IT费用是多少？
# 分析：
# - 年份：FY25
# - 场景：Actual
# - Function：IT Allocation（分摊题必须使用Allocation Function）
# - 分摊维度：CT（业务线），使用t7.[BL]字段
# - 分摊值：CT（需要确认具体的业务线值，这里假设为'CT'）

def build_sql() -> str:
    return generate_alloc_sql(
        years=["FY25"],  # 25财年
        scenarios=["Actual"],  # 实际
        function_name="IT Allocation",  # IT分摊题必须使用IT Allocation
        party_field="t7.[BL]",  # CT对应业务线维度
        party_value="CT",  # 业务线值为CT
    )

if __name__ == "__main__":
    sql = build_sql()
    print("生成的SQL查询：")
    print(sql)
    print("\n" + "="*80 + "\n")
    
    # 执行SQL查询
    # 注意：这里需要sqlquery工具来执行，我无法直接执行
    # 但可以展示SQL结构
    print("SQL查询结构说明：")
    print("1. monthly_alloc CTE：按月计算分摊金额")
    print("2. yearly_agg CTE：按年汇总分摊金额")
    print("3. 最终查询：返回FY25年的分摊总金额")
    print("\n需要执行此SQL来获取具体金额。")