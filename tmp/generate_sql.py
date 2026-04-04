import sys
sys.path.insert(0, '/skills/finance/scripts')
from allocation_utils import generate_alloc_sql

# Generate SQL for FY26 Budget
fy26_budget_sql = generate_alloc_sql(
    years=["FY26"],
    scenarios=["Budget1"],
    function_name="HR Allocation",
    party_field="t7.[CC]",
    party_value="4130011"
)

# Generate SQL for FY25 Actual
fy25_actual_sql = generate_alloc_sql(
    years=["FY25"],
    scenarios=["Actual"],
    function_name="HR Allocation",
    party_field="t7.[CC]",
    party_value="4130011"
)

print("FY26 SQL:")
print(fy26_budget_sql)
print("\n" + "="*80 + "\n")
print("FY25 SQL:")
print(fy25_actual_sql)
