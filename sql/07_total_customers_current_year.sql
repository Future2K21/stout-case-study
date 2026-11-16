-- Customer count. Comparison metrics are NULL when the prior year is absent.
SELECT
    report_year,
    SUM(in_current) AS total_customers_current_year
FROM customer_comparison
GROUP BY report_year, has_prior_year
ORDER BY report_year;
