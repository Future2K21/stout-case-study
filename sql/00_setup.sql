-- run_case.py loads raw_orders before executing this script.
CREATE TABLE customer_year AS
SELECT order_year, customer_id, SUM(revenue_cents) AS revenue_cents
FROM raw_orders
GROUP BY order_year, customer_id;

CREATE TABLE report_years AS
SELECT DISTINCT order_year AS report_year
FROM customer_year;

-- Each customer-year is current for its own year and prior for the next year.
-- Keep both populations, including prior-only customers who were lost.
CREATE TABLE customer_comparison AS
WITH aligned AS (
    SELECT order_year AS report_year, customer_id,
           1 AS in_current, 0 AS in_prior,
           revenue_cents AS current_cents, NULL AS prior_cents
    FROM customer_year
    UNION ALL
    SELECT order_year + 1, customer_id, 0, 1, NULL, revenue_cents
    FROM customer_year
)
SELECT
    aligned.report_year,
    aligned.customer_id,
    EXISTS (
        SELECT 1 FROM report_years AS prior
        WHERE prior.report_year = aligned.report_year - 1
    ) AS has_prior_year,
    MAX(in_current) AS in_current,
    MAX(in_prior) AS in_prior,
    MAX(current_cents) AS current_cents,
    MAX(prior_cents) AS prior_cents
FROM aligned
JOIN report_years USING (report_year)
GROUP BY aligned.report_year, aligned.customer_id;
