from typing import List

ALLOC_TEMPLATE = """WITH monthly_alloc AS (
    SELECT
        cdb.year,
        cdb.month,
        cdb.key,
        cdb.amount AS base_cost,
        COALESCE(
            CAST(cdb.amount AS NUMERIC) * 
            COALESCE(
                CASE 
                    WHEN REPLACE(rt.rate_no::TEXT, '%', '')::NUMERIC > 1 
                    THEN REPLACE(rt.rate_no::TEXT, '%', '')::NUMERIC / 100
                    ELSE REPLACE(rt.rate_no::TEXT, '%', '')::NUMERIC
                END, 
                0
            ),
            0
        ) AS allocated_cost
    FROM cost_database cdb
    LEFT JOIN rate_table rt
        ON cdb.year = rt.year
        AND cdb.scenario = rt.scenario
        AND cdb.key = rt.key
        AND cdb.month = rt.month
        AND {party_filter}
    WHERE {year_filter}
        AND {scenario_filter}
        AND cdb.function = {function_literal}
),
yearly_agg AS (
    SELECT
        year,
        SUM(allocated_cost) AS total_allocated_cost
    FROM monthly_alloc
    GROUP BY year
)
SELECT
    year,
    total_allocated_cost
FROM yearly_agg
WHERE {year_filter_output};"""

def _quote_literal(value: str) -> str:
    return "'{}'".format(value.replace("'", "''"))

def _build_or_list(items: List[str], field_name: str) -> str:
    if not items:
        return "1=1"
    literals = [_quote_literal(item) for item in items]
    if len(literals) == 1:
        return f"{field_name} = {literals[0]}"
    return "(" + " OR ".join([f"{field_name} = {val}" for val in literals]) + ")"

def generate_alloc_sql(
    years: List[str],
    scenarios: List[str],
    function_name: str,
    party_field: str,
    party_value: str,
) -> str:
    year_filter = _build_or_list(years, "cdb.year")
    year_filter_output = _build_or_list(years, year)
    scenario_filter = _build_or_list(scenarios, "cdb.scenario")
    function_literal = _quote_literal(function_name)
    if isinstance(party_value, str) and not party_value.isdigit():
        party_value_literal = _quote_literal(party_value)
    else:
        party_value_literal = party_value
    party_filter = f"{party_field} = {party_value_literal}"
    return ALLOC_TEMPLATE.format(
        year_filter=year_filter,
        year_filter_output=year_filter_output,
        scenario_filter=scenario_filter,
        function_literal=function_literal,
        party_filter=party_filter,
    )
