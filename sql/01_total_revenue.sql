-- Integer cents. Comparison metrics are NULL when the prior year is absent.
SELECT
    report_year,
    SUM(current_cents) AS total_revenue
FROM customer_comparison
GROUP BY report_year, has_prior_year
ORDER BY report_year;
