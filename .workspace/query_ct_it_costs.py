from skills.finance.scripts.allocation_utils import generate_alloc_sql
from skills.finance.scripts.sql_query import run_sql_query

def query_ct_it_costs():
    # Define parameters for the query
    years = ["2025"]  # 25财年
    scenarios = ["Actual"]  # 实际分摊
    function_name = "IT"  # IT费用
    party_field = "cdb.[Party]"
    party_value = "CT"  # 分摊给CT

    # Generate SQL query
    sql_query = generate_alloc_sql(years, scenarios, function_name, party_field, party_value)

    # Execute the query
    result = run_sql_query(sql_query)

    return result

if __name__ == "__main__":
    output = query_ct_it_costs()
    print(output)