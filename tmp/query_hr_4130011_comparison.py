#!/usr/bin/env python3
"""
查询HR Allocation分摊给Cost Center 4130011的对比：
- FY26 BGT (Budget1) 分摊给4130011的HR费用
- FY25 Actual 分摊给4130011的HR费用
"""
import sys
import os
import json

# 添加技能路径到系统路径
sys.path.append('/skills/finance/scripts')

from allocation_utils import generate_alloc_sql
from sql_query import run_sql_query

def query_fy26_budget_4130011():
    """查询FY26 Budget分摊给4130011的HR Allocation费用"""
    return generate_alloc_sql(
        years=["FY26"],
        scenarios=["Budget1"],
        function_name="HR Allocation",
        party_field="t7.[CC]",
        party_value="4130011"
    )

def query_fy25_actual_4130011():
    """查询FY25 Actual分摊给4130011的HR Allocation费用"""
    return generate_alloc_sql(
        years=["FY25"],
        scenarios=["Actual"],
        function_name="HR Allocation",
        party_field="t7.[CC]",
        party_value="4130011"
    )

if __name__ == "__main__":
    print("=" * 80)
    print("查询HR Allocation分摊给Cost Center 4130011的对比")
    print("=" * 80)
    print()
    
    # 生成SQL
    sql_fy26 = query_fy26_budget_4130011()
    sql_fy25 = query_fy25_actual_4130011()
    
    print("=" * 80)
    print("FY26 BGT SQL:")
    print("=" * 80)
    print(sql_fy26)
    print()
    
    print("=" * 80)
    print("FY25 Actual SQL:")
    print("=" * 80)
    print(sql_fy25)
    print()
    
    # 执行查询
    print("=" * 80)
    print("执行查询...")
    print("=" * 80)
    
    result_fy26 = run_sql_query(sql_fy26)
    result_fy25 = run_sql_query(sql_fy25)
    
    print("\nFY26 BGT 结果:")
    print(result_fy26)
    
    print("\nFY25 Actual 结果:")
    print(result_fy25)
    
    # 解析并计算差异
    try:
        data_fy26 = json.loads(result_fy26)
        data_fy25 = json.loads(result_fy25)
        
        fy26_value = 0
        fy25_value = 0
        
        if data_fy26.get('rows') and len(data_fy26['rows']) > 0:
            fy26_value = float(data_fy26['rows'][0].get('Year_Allocated_Cost', 0))
        
        if data_fy25.get('rows') and len(data_fy25['rows']) > 0:
            fy25_value = float(data_fy25['rows'][0].get('Year_Allocated_Cost', 0))
        
        difference = fy26_value - fy25_value
        pct_change = ((fy26_value - fy25_value) / fy25_value * 100) if fy25_value != 0 else 0
        
        print("\n" + "=" * 80)
        print("对比结果 - HR Allocation 分摊给 Cost Center 4130011")
        print("=" * 80)
        print(f"FY25 Actual:     ${fy25_value:,.2f}")
        print(f"FY26 Budget:     ${fy26_value:,.2f}")
        print(f"差异 (FY26 - FY25):  ${difference:,.2f}")
        print(f"变化百分比:      {pct_change:,.2f}%")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n解析结果时出错: {e}")
