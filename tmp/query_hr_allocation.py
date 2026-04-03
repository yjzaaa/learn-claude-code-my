#!/usr/bin/env python3
"""Script to query HR Allocation data for cost center 4130011 comparing FY26 Budget vs FY25 Actual."""

import sys
import json
sys.path.insert(0, '/skills/finance/scripts')

from allocation_utils import generate_alloc_sql
from sql_query import run_sql_query

# Generate SQL for FY26 Budget
fy26_budget_sql = generate_alloc_sql(
    years=["FY26"],
    scenarios=["Budget1"],
    function_name="HR Allocation",
    party_field="t7.[CC]",
    party_value="4130011"
)

print("=" * 80)
print("FY26 BUDGET SQL QUERY")
print("=" * 80)
print(fy26_budget_sql)
print()

# Generate SQL for FY25 Actual
fy25_actual_sql = generate_alloc_sql(
    years=["FY25"],
    scenarios=["Actual"],
    function_name="HR Allocation",
    party_field="t7.[CC]",
    party_value="4130011"
)

print("=" * 80)
print("FY25 ACTUAL SQL QUERY")
print("=" * 80)
print(fy25_actual_sql)
print()

# Execute queries
print("=" * 80)
print("EXECUTING QUERIES")
print("=" * 80)

print("\nExecuting FY26 Budget query...")
fy26_result = run_sql_query(fy26_budget_sql)
print(f"FY26 Budget Result: {fy26_result}")

print("\nExecuting FY25 Actual query...")
fy25_result = run_sql_query(fy25_actual_sql)
print(f"FY25 Actual Result: {fy25_result}")

# Parse results and calculate difference
try:
    fy26_data = json.loads(fy26_result)
    fy25_data = json.loads(fy25_result)
    
    fy26_value = 0
    fy25_value = 0
    
    if fy26_data.get('rows') and len(fy26_data['rows']) > 0:
        fy26_value = float(fy26_data['rows'][0].get('Year_Allocated_Cost', 0))
    
    if fy25_data.get('rows') and len(fy25_data['rows']) > 0:
        fy25_value = float(fy25_data['rows'][0].get('Year_Allocated_Cost', 0))
    
    difference = fy26_value - fy25_value
    pct_change = ((fy26_value - fy25_value) / fy25_value * 100) if fy25_value != 0 else 0
    
    print("\n" + "=" * 80)
    print("COMPARISON RESULTS - HR ALLOCATION TO COST CENTER 4130011")
    print("=" * 80)
    print(f"FY25 Actual:     ${fy25_value:,.2f}")
    print(f"FY26 Budget:     ${fy26_value:,.2f}")
    print(f"Difference:      ${difference:,.2f}")
    print(f"Percent Change:  {pct_change:,.2f}%")
    print("=" * 80)
    
except Exception as e:
    print(f"\nError parsing results: {e}")
