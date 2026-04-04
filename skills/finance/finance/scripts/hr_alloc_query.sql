WITH monthly_alloc AS (
    SELECT
        cdb.year,
        cdb.scenario,
        COALESCE(SUM(CAST(cdb.amount AS FLOAT)), 0) AS Base_Month_Cost,
        COALESCE(
            SUM(
                CAST(cdb.amount AS FLOAT) * 
                COALESCE(
                    CASE 
                        WHEN REPLACE(rate.rateno, '%', '')::numeric > 1 
                        THEN REPLACE(rate.rateno, '%', '')::numeric / 100
                        ELSE REPLACE(rate.rateno, '%', '')::numeric
                    END, 
                    0
                )
            ), 
            0
        ) AS Allocated_Month_Cost
    FROM cost_database cdb
    LEFT JOIN ssme_fi_insightbot_rate rate
        ON cdb.year = rate.year
        AND cdb.scenario = rate.scenario
        AND cdb.key = rate.key
        AND cdb.month = rate.month
    WHERE cdb.year IN ('FY25', 'FY26')
        AND cdb.scenario IN ('Actual', 'Budget1')
        AND cdb.function = 'HR Allocation'
        AND rate.cc = '413001'
    GROUP BY cdb.year, cdb.scenario, cdb.month
),
yearly_agg AS (
    SELECT
        year,
        scenario,
        SUM(Allocated_Month_Cost) AS Year_Allocated_Cost
    FROM monthly_alloc
    GROUP BY year, scenario
)
SELECT * FROM yearly_agg ORDER BY year, scenario
