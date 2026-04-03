WITH monthly_alloc AS (
    SELECT
        cdb.year,
        COALESCE(SUM(CAST(cdb.amount AS FLOAT)), 0) AS base_month_cost,
        COALESCE(
            SUM(
                CAST(cdb.amount AS FLOAT) * 
                COALESCE(
                    CASE 
                        WHEN TRY_CAST(REPLACE(t7.rateno, '%', '') AS FLOAT) > 1 
                        THEN TRY_CAST(REPLACE(t7.rateno, '%', '') AS FLOAT) / 100
                        ELSE TRY_CAST(REPLACE(t7.rateno, '%', '') AS FLOAT)
                    END, 
                    0
                )
            ), 
            0
        ) AS allocated_month_cost
    FROM cost_database cdb
    LEFT JOIN rate_table t7
        ON cdb.year = t7.year
        AND cdb.scenario = t7.scenario
        AND cdb.key = t7.key
        AND cdb.month = t7.month
    WHERE cdb.year = 'FY25'
        AND cdb.scenario = 'Actual'
        AND cdb.function = 'IT Allocation'
        AND t7.bl = 'CT'
    GROUP BY cdb.year
),
yearly_agg AS (
    SELECT
        year,
        SUM(allocated_month_cost) AS year_allocated_cost
    FROM monthly_alloc
    GROUP BY year
)
SELECT
    year,
    year_allocated_cost
FROM yearly_agg
WHERE year = 'FY25';