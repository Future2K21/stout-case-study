-- Integer cents. Comparison metrics are NULL when the prior year is absent.
SELECT
    report_year,
    CASE WHEN has_prior_year = 1 THEN
        SUM(CASE
            WHEN in_current = 0 AND in_prior = 1
            THEN prior_cents
            ELSE 0
        END)
    END AS revenue_lost_from_attrition
FROM customer_comparison
GROUP BY report_year, has_prior_year
ORDER BY report_year;
