WITH Allocated_Cost_CTE AS (
    SELECT 
        cdb.[Year],
        cdb.[Scenario],
        cdb.[Function],
        cdb.[Month],
        COALESCE(SUM(CAST(cdb.[Amount] AS FLOAT) * 
            COALESCE(
                CASE WHEN TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT) > 1 THEN TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT) / 100
                ELSE TRY_CAST(REPLACE(t7.[RateNo], '%', '') AS FLOAT)
                END, 0)), 0) AS [Allocated_Cost]
    FROM 
        [SSME_FI_InsightBot_CostDataBase] AS cdb
    LEFT JOIN 
        [SSME_FI_InsightBot_AllocationRules] AS t7
    ON 
        cdb.[Key] = t7.[Key]
    WHERE 
        cdb.[Year] = 'FY25' AND 
        cdb.[Scenario] = 'Actual' AND 
        cdb.[Function] = 'IT Allocation' AND 
        t7.[Allocated_BL] = 'CT'
    GROUP BY 
        cdb.[Year], cdb.[Scenario], cdb.[Function], cdb.[Month]
)
SELECT 
    [Year],
    [Scenario],
    [Function],
    COALESCE(SUM([Allocated_Cost]), 0) AS [Total_Allocated_Cost]
FROM 
    Allocated_Cost_CTE
GROUP BY 
    [Year], [Scenario], [Function];