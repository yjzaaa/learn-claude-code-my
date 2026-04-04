"""
PostgreSQL 分摊计算工具模块
用于生成 HR/IT Allocation 分摊查询的 SQL
"""

from typing import List, Optional


# HR Allocation 分摊查询模板
HR_ALLOC_TEMPLATE = """
SELECT 
    c.year,
    c.scenario,
    SUM(c.amount * CAST(r.rate_no AS NUMERIC)) as total_allocated_amount
FROM cost_database c
JOIN ssme_fi_insightbot_rate r 
    ON c.year = r.year 
    AND c.scenario = r.scenario
    AND c.month = r.month
    AND c.key = r.key
WHERE c.function = 'HR Allocation'
    AND c.account = '91800150.0'
    AND r.cc = '{target_cc}'
    AND r.key = '480055 Cycle'
    AND c.scenario IN ({scenarios})
    AND c.year IN ({years})
GROUP BY c.year, c.scenario
ORDER BY c.year, c.scenario
"""

# IT Allocation 分摊查询模板
IT_ALLOC_TEMPLATE = """
SELECT 
    c.year,
    c.scenario,
    SUM(c.amount * CAST(r.rate_no AS NUMERIC)) as total_allocated_amount
FROM cost_database c
JOIN ssme_fi_insightbot_rate r 
    ON c.year = r.year 
    AND c.scenario = r.scenario
    AND c.month = r.month
    AND c.key = r.key
WHERE c.function = 'IT Allocation'
    AND r.cc = '{target_cc}'
    AND r.key = '480056 Cycle'
    AND c.scenario IN ({scenarios})
    AND c.year IN ({years})
GROUP BY c.year, c.scenario
ORDER BY c.year, c.scenario
"""

# 对比分析模板（含变化率）
COMPARISON_TEMPLATE = """
WITH allocation_data AS (
    SELECT 
        c.year,
        c.scenario,
        SUM(c.amount * CAST(r.rate_no AS NUMERIC)) as allocated_amount
    FROM cost_database c
    JOIN ssme_fi_insightbot_rate r 
        ON c.year = r.year 
        AND c.scenario = r.scenario
        AND c.month = r.month
        AND c.key = r.key
    WHERE c.function = '{allocation_function}'
        AND r.cc = '{target_cc}'
        AND r.key = '{cycle_key}'
        AND c.scenario IN ({scenarios})
        AND c.year IN ({years})
    GROUP BY c.year, c.scenario
)
SELECT 
    year,
    scenario,
    allocated_amount,
    LAG(allocated_amount) OVER (ORDER BY year, scenario) as prev_amount,
    CASE 
        WHEN LAG(allocated_amount) OVER (ORDER BY year, scenario) != 0 
        THEN (allocated_amount - LAG(allocated_amount) OVER (ORDER BY year, scenario)) 
             / LAG(allocated_amount) OVER (ORDER BY year, scenario) * 100
        ELSE 0 
    END as change_pct
FROM allocation_data
"""


def _format_list(items: List[str]) -> str:
    """将列表格式化为 SQL IN 子句字符串"""
    return ", ".join([f"'{item}'" for item in items])


def normalize_cc(cc_input: str) -> str:
    """
    标准化 CC 输入
    - 如果输入是 7 位（如 4130011），尝试截取前 6 位（413001）
    - 返回标准化后的 CC 值
    """
    cc_clean = cc_input.strip()
    
    # 数据库中 CC 是 6 位数字
    if len(cc_clean) == 7 and cc_clean.startswith('413'):
        return cc_clean[:6]  # 截取前 6 位
    
    return cc_clean


def generate_hr_allocation_sql(
    target_cc: str,
    years: List[str] = None,
    scenarios: List[str] = None
) -> str:
    """
    生成 HR Allocation 分摊查询 SQL
    
    Args:
        target_cc: 目标成本中心（如 '413001'）
        years: 年份列表（如 ['FY25', 'FY26']）
        scenarios: 场景列表（如 ['Actual', 'Budget1']）
    
    Returns:
        可执行的 PostgreSQL SQL 语句
    """
    if years is None:
        years = ['FY25', 'FY26']
    if scenarios is None:
        scenarios = ['Actual', 'Budget1']
    
    normalized_cc = normalize_cc(target_cc)
    
    return HR_ALLOC_TEMPLATE.format(
        target_cc=normalized_cc,
        years=_format_list(years),
        scenarios=_format_list(scenarios)
    )


def generate_it_allocation_sql(
    target_cc: str,
    years: List[str] = None,
    scenarios: List[str] = None
) -> str:
    """
    生成 IT Allocation 分摊查询 SQL
    
    Args:
        target_cc: 目标成本中心（如 '413001'）
        years: 年份列表（如 ['FY25', 'FY26']）
        scenarios: 场景列表（如 ['Actual', 'Budget1']）
    
    Returns:
        可执行的 PostgreSQL SQL 语句
    """
    if years is None:
        years = ['FY25', 'FY26']
    if scenarios is None:
        scenarios = ['Actual', 'Budget1']
    
    normalized_cc = normalize_cc(target_cc)
    
    return IT_ALLOC_TEMPLATE.format(
        target_cc=normalized_cc,
        years=_format_list(years),
        scenarios=_format_list(scenarios)
    )


def generate_comparison_sql(
    allocation_type: str,  # 'HR' or 'IT'
    target_cc: str,
    years: List[str] = None,
    scenarios: List[str] = None
) -> str:
    """
    生成分摊对比分析 SQL（含变化率）
    
    Args:
        allocation_type: 'HR' 或 'IT'
        target_cc: 目标成本中心
        years: 年份列表
        scenarios: 场景列表
    
    Returns:
        可执行的 PostgreSQL SQL 语句
    """
    if years is None:
        years = ['FY25', 'FY26']
    if scenarios is None:
        scenarios = ['Actual', 'Budget1']
    
    normalized_cc = normalize_cc(target_cc)
    
    if allocation_type.upper() == 'HR':
        allocation_function = 'HR Allocation'
        cycle_key = '480055 Cycle'
    else:
        allocation_function = 'IT Allocation'
        cycle_key = '480056 Cycle'
    
    return COMPARISON_TEMPLATE.format(
        allocation_function=allocation_function,
        target_cc=normalized_cc,
        cycle_key=cycle_key,
        years=_format_list(years),
        scenarios=_format_list(scenarios)
    )


# 向后兼容的别名
generate_alloc_sql = generate_hr_allocation_sql
