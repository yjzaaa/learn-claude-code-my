from skills.finance.scripts.sql_query import run_sql_query

# SQL Query to calculate FY25 Actual IT Allocation to CT
sql_query = """
WITH normalized_rate AS (
    SELECT
        t7.[Year],
        t7.[Scenario],
        t7.[Month],
        t7.[Key],
        t7.[CC],
        t7.[BL],
        TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT) / CASE WHEN TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT) > 1 THEN 100 ELSE 1 END AS normalized_rate_no
    FROM SSME_FI_InsightBot_Rate AS t7
    WHERE t7.[Year] = '2025' AND t7.[Scenario] = 'Actual' AND t7.[Key] = '480056 Cycle'
),
monthly_cost AS (
    SELECT
        cdb.[Year],
        cdb.[Scenario],
        cdb.[Month],
        cdb.[Function],
        cdb.[Key],
        cdb.[Cost text],
        cdb.[Amount],
        CAST(cdb.[Amount] AS FLOAT) * COALESCE(nr.normalized_rate_no, 0) AS allocated_amount
    FROM SSME_FI_InsightBot_CostDataBase AS cdb
    LEFT JOIN normalized_rate AS nr
        ON cdb.[Year] = nr.[Year] AND cdb.[Scenario] = nr.[Scenario] AND cdb.[Key] = nr.[Key] AND cdb.[Month] = nr.[Month]
    WHERE cdb.[Year] = '2025' AND cdb.[Scenario] = 'Actual' AND cdb.[Function] = 'IT Allocation' AND cdb.[Key] = '480056 Cycle'
)
SELECT
    SUM(mc.allocated_amount) AS total_allocated_amount
FROM monthly_cost AS mc;
"""

result = run_sql_query(sql_query)
print(result)