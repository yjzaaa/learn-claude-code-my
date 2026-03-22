WITH monthly_alloc AS (
    SELECT
        cdb.year,
        COALESCE(SUM(cdb.amount::float), 0) AS base_month_cost,
        COALESCE(
            SUM(
                cdb.amount::float * 
                COALESCE(
                    CASE 
                        WHEN REPLACE(t7.rate_no, '%', '') ~ '^[0-9]+(\.[0-9]+)?$'
                        THEN 
                            CASE 
                                WHEN REPLACE(t7.rate_no, '%', '')::float > 1 
                                THEN REPLACE(t7.rate_no, '%', '')::float / 100
                                ELSE REPLACE(t7.rate_no, '%', '')::float
                            END
                        ELSE 0
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