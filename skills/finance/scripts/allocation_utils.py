from typing import List

ALLOC_TEMPLATE = """WITH monthly_alloc AS (
    SELECT
        cdb.[Year],
        COALESCE(SUM(CAST(cdb.[Amount] AS FLOAT)), 0) AS [Base_Month_Cost],
        COALESCE(
            SUM(
                CAST(cdb.[Amount] AS FLOAT) * 
                COALESCE(
                    CASE 
                        WHEN TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT) > 1 
                        THEN TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT) / 100
                        ELSE TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT)
                    END, 
                    0
                )
            ), 
            0
        ) AS [Allocated_Month_Cost]
    FROM SSME_FI_InsightBot_CostDataBase cdb
    LEFT JOIN SSME_FI_InsightBot_Rate t7
        ON cdb.[Year] = t7.[Year]
        AND cdb.[Scenario] = t7.[Scenario]
        AND cdb.[Key] = t7.[Key]
        AND cdb.[Month] = t7.[Month]
    WHERE {year_filter}
        AND {scenario_filter}
        AND cdb.[Function] = {function_literal}
        AND {party_filter}
    GROUP BY cdb.Year
),
yearly_agg AS (
    SELECT
        [Year],
        SUM([Allocated_Month_Cost]) AS [Year_Allocated_Cost]
    FROM monthly_alloc
    GROUP BY [Year]
)
SELECT
    [Year],
    [Year_Allocated_Cost]
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
    year_filter_output = _build_or_list(years, "year")
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