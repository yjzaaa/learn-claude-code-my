-- 26财年HR费用预算查询SQL语句

-- 1. 查询总预算
SELECT SUM(year_total) as total_hr_budget_fy26
FROM cost_database 
WHERE year = 'FY26' 
  AND scenario = 'Budget1' 
  AND function = 'HR';

-- 2. 查询详细分类（按cost_text分组）
SELECT 
    function,
    cost_text,
    key,
    SUM(amount) as monthly_total,
    SUM(year_total) as annual_total
FROM cost_database 
WHERE year = 'FY26' 
  AND scenario = 'Budget1' 
  AND function = 'HR'
GROUP BY function, cost_text, key
ORDER BY annual_total DESC;

-- 3. 查询月度分布
SELECT 
    month,
    SUM(amount) as monthly_amount
FROM cost_database 
WHERE year = 'FY26' 
  AND scenario = 'Budget1' 
  AND function = 'HR'
GROUP BY month
ORDER BY month;

-- 4. 计算各项占比
WITH hr_total AS (
    SELECT SUM(year_total) as total FROM cost_database 
    WHERE year = 'FY26' AND scenario = 'Budget1' AND function = 'HR'
),
hr_detail AS (
    SELECT 
        cost_text,
        SUM(year_total) as annual_total
    FROM cost_database 
    WHERE year = 'FY26' AND scenario = 'Budget1' AND function = 'HR'
    GROUP BY cost_text
)
SELECT 
    d.cost_text,
    d.annual_total,
    ROUND(d.annual_total / t.total * 100, 2) as percentage
FROM hr_detail d
CROSS JOIN hr_total t
ORDER BY d.annual_total DESC;

-- 5. 查询平均月度预算
SELECT 
    AVG(monthly_amount) as avg_monthly_budget,
    COUNT(DISTINCT month) as months_count
FROM (
    SELECT 
        month,
        SUM(amount) as monthly_amount
    FROM cost_database 
    WHERE year = 'FY26' 
      AND scenario = 'Budget1' 
      AND function = 'HR'
    GROUP BY month
) monthly_data;

-- 6. 查询预算构成（按key分类）
SELECT 
    key,
    COUNT(*) as record_count,
    SUM(year_total) as total_by_key,
    ROUND(SUM(year_total) / (SELECT SUM(year_total) FROM cost_database 
        WHERE year = 'FY26' AND scenario = 'Budget1' AND function = 'HR') * 100, 2) as percentage
FROM cost_database 
WHERE year = 'FY26' 
  AND scenario = 'Budget1' 
  AND function = 'HR'
GROUP BY key
ORDER BY total_by_key DESC;