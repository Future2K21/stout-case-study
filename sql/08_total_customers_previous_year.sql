-- Customer count. Comparison metrics are NULL when the prior year is absent.
SELECT
    report_year,
    CASE WHEN has_prior_year = 1 THEN
        SUM(in_prior)
    END AS total_customers_previous_year
FROM customer_comparison
GROUP BY report_year, has_prior_year
ORDER BY report_year;
