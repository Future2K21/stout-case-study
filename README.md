# Stout Customer Revenue Case Study

This analysis reports ten annual revenue and customer metrics for 2015–2017. The Tableau dashboard includes a yearly scorecard, a total revenue trend, and a breakdown of the drivers of revenue change.

[View the Stout Case Study Tableau dashboard](https://public.tableau.com/app/profile/donovan.lane/viz/Stout_Case_Study/CustomerRevenueandRetention)

## Reproduce the analysis

Place `casestudy.csv` in the same folder as `run_case.py`. Run the following with Python 3:

```bash
python run_case.py casestudy.csv
```

On Windows, use `py` in place of `python` if that is your Python command. If your source file is named `customer_orders.csv`, pass that filename instead.

The script uses Python’s built-in SQLite module to load the CSV, run `sql/00_setup.sql` and queries 01–10, and reconcile annual revenue and customer counts against the source data. It writes `results/annual_metrics.csv` for Tableau and `results/findings_notes.md` for the aggregate findings.

## Metric definitions

- **New customers** appear in the current year only.
- **Retained customers** appear in both the current year and the immediately preceding year.
- **Lost customers** appear in the preceding year only.

Prior-year comparisons are unavailable for 2015 because the source begins in 2015. The revenue drivers chart shows attrition as a negative contribution based on lost customers’ prior-year revenue. Revenue figures use the source data’s currency units.