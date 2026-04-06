"""
分摊计算示例和验证脚本
展示如何正确使用 RateNo 进行分摊计算
"""

import sys
from pathlib import Path

# 添加当前目录到模块搜索路径
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from pg_allocation_utils import (
    generate_hr_allocation_sql,
    generate_it_allocation_sql,
    generate_comparison_sql,
    normalize_cc
)


def example_hr_allocation_to_cc():
    """
    示例：HR Allocation 分摊到 413001 的对比查询
    对应用户问题："How is the change of HR allocation to 4130011 between FY26 BGT and FY25 Actual"
    """
    print("=" * 60)
    print("示例：HR Allocation 分摊到 413001")
    print("=" * 60)

    # 用户输入 4130011，但数据库中是 413001
    user_input_cc = "4130011"
    normalized_cc = normalize_cc(user_input_cc)
    print(f"\n用户输入 CC: {user_input_cc}")
    print(f"标准化后 CC: {normalized_cc}")

    # 生成 SQL
    sql = generate_hr_allocation_sql(
        target_cc=user_input_cc,
        years=['FY25', 'FY26'],
        scenarios=['Actual', 'Budget1']
    )

    print("\n生成的 SQL:")
    print(sql)

    print("\n预期结果:")
    print("- FY25 Actual: -241,612.80")
    print("- FY26 BGT: -216,978.89")
    print("- 变化: +24,633.91 (减少约 10.2%)")
    print("\nRateNo 说明:")
    print("- FY25 Actual RateNo: 0.020800 (2.08%)")
    print("- FY26 BGT RateNo: 0.018000 (1.80%)")
    print("- 计算: Monthly Amount × RateNo (小数形式，无需除以100)")

    return sql


def example_it_allocation():
    """示例：IT Allocation 分摊查询"""
    print("\n" + "=" * 60)
    print("示例：IT Allocation 分摊到 413001")
    print("=" * 60)

    sql = generate_it_allocation_sql(
        target_cc="413001",
        years=['FY25', 'FY26'],
        scenarios=['Actual', 'Budget1']
    )

    print("\n生成的 SQL:")
    print(sql)

    return sql


def example_comparison():
    """示例：带变化率的对比分析"""
    print("\n" + "=" * 60)
    print("示例：HR Allocation 对比分析（含变化率）")
    print("=" * 60)

    sql = generate_comparison_sql(
        allocation_type='HR',
        target_cc='413001',
        years=['FY25', 'FY26'],
        scenarios=['Actual', 'Budget1']
    )

    print("\n生成的 SQL:")
    print(sql)

    return sql


def key_points():
    """关键要点总结"""
    print("\n" + "=" * 60)
    print("关键要点总结")
    print("=" * 60)

    points = [
        ("1. RateNo 处理", [
            "数据库中 RateNo 存储为小数字符串（如 '0.020800'）",
            "直接使用 CAST(rate_no AS NUMERIC)，无需除以 100",
            "表示 2.08%，不是 0.0208%"
        ]),
        ("2. Function 选择", [
            "分摊题必须使用 'HR Allocation' 或 'IT Allocation'",
            "禁止使用 'HR' 或 'IT'（这是普通费用）"
        ]),
        ("3. Key 映射", [
            "HR Allocation -> '480055 Cycle'",
            "IT Allocation -> '480056 Cycle'"
        ]),
        ("4. CC 字段匹配", [
            "数据库中 CC 是 6 位数字（如 413001）",
            "用户可能输入 4130011（7位），需要标准化处理"
        ]),
        ("5. 四重 JOIN", [
            "year, scenario, month, key 四个字段必须同时关联",
            "确保按月计算分摊金额"
        ]),
        ("6. PostgreSQL 语法", [
            "字段名使用双引号（如 \"Year\"）",
            "字符串使用单引号（如 'Budget1'）"
        ])
    ]

    for title, items in points:
        print(f"\n{title}:")
        for item in items:
            print(f"  - {item}")


if __name__ == "__main__":
    # 运行所有示例
    example_hr_allocation_to_cc()
    example_it_allocation()
    example_comparison()
    key_points()
