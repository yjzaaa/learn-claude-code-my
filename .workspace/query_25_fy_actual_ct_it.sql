SELECT SUM(Allocated_Amount) AS Total_IT_Cost
FROM SSME_FI_InsightBot_CostDataBase
WHERE [Scenario] = 'Actual'
  AND [Function] = 'IT Allocation'
  AND [Year] = 2025
  AND [Rate.BL] = 'CT';