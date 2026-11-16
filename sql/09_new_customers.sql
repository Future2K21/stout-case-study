-- Customer count. Comparison metrics are NULL when the prior year is absent.
SELECT
    report_year,
    CASE WHEN has_prior_year = 1 THEN
        SUM(CASE WHEN in_current = 1 AND in_prior = 0 THEN 1 ELSE 0 END)
    END AS new_customers
FROM customer_comparison
GROUP BY report_year, has_prior_year
ORDER BY report_year;
