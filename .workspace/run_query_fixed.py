from sql_query import run_sql_query

query = '''
SELECT 
    COALESCE(SUM(CAST(cdb.[Amount] AS FLOAT) * 
    TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT) / 100), 0) AS [分摊金额]
FROM 
    SSME_FI_InsightBot_CostDataBase AS cdb
LEFT JOIN 
    SSME_FI_InsightBot_Rate AS t7
ON 
    cdb.[Year] = t7.[Year] 
    AND cdb.[Scenario] = t7.[Scenario] 
    AND cdb.[Key] = t7.[Key] 
    AND cdb.[Month] = t7.[Month]
WHERE 
    cdb.[Year] = '25' 
    AND cdb.[Scenario] = 'Actual' 
    AND cdb.[Function] = 'IT Allocation' 
    AND cdb.[Key] = '480056 Cycle' 
    AND t7.[CC] = 'CT';
'''

result = run_sql_query(query)
print(result)