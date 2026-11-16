import argparse
import csv
import re
import sqlite3
from contextlib import closing
from decimal import Decimal, InvalidOperation
from pathlib import Path


SQL_DIR = Path(__file__).resolve().parent / "sql"
REQUIRED_HEADERS = ("customer_email", "net_revenue", "year")


def read_orders(csv_path):
    with csv_path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        headers = {}
        for original in reader.fieldnames or ():
            normalized = re.sub(r"\s+", "_", original.strip().lower())
            if normalized and normalized in headers:
                raise ValueError(f"Ambiguous column header: {original}")
            headers[normalized] = original

        missing = [name for name in REQUIRED_HEADERS if name not in headers]
        if missing:
            raise ValueError(f"Missing columns: {', '.join(missing)}")

        for row in reader:
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError
                customer_id = row[headers["customer_email"]].strip()
                year = int(row[headers["year"]])
                revenue = Decimal(row[headers["net_revenue"]].strip())
                if not customer_id or not 1000 <= year <= 9999 or not revenue.is_finite():
                    raise ValueError
                if revenue.adjusted() > 15:
                    raise ValueError
                cents = revenue * 100
                if cents != cents.to_integral_value():
                    raise ValueError
            except (ValueError, InvalidOperation):
                raise ValueError(
                    f"CSV line {reader.line_num} needs a customer ID, a four-digit "
                    "year, and a finite net revenue amount in whole cents."
                ) from None
            yield (customer_id, year, int(cents))


def run_queries(db, csv_path):
    db.execute(
        """CREATE TABLE raw_orders (
               customer_id TEXT NOT NULL,
               order_year INTEGER NOT NULL,
               revenue_cents INTEGER NOT NULL
           )"""
    )
    db.executemany("INSERT INTO raw_orders VALUES (?, ?, ?)", read_orders(csv_path))
    source = {
        year: (revenue, customers)
        for year, revenue, customers in db.execute(
            """SELECT order_year, SUM(revenue_cents), COUNT(DISTINCT customer_id)
               FROM raw_orders GROUP BY order_year ORDER BY order_year"""
        )
    }
    if not source:
        raise ValueError("The CSV contains no data rows.")

    setup_sql = (SQL_DIR / "00_setup.sql").read_text(encoding="utf-8")
    db.executescript(setup_sql)
    queries = sorted(path for path in SQL_DIR.glob("[0-9][0-9]_*.sql")
                     if path.name != "00_setup.sql")
    if [path.name[:2] for path in queries] != [f"{n:02}" for n in range(1, 11)]:
        raise ValueError("Expected one SQL metric file for each number 01 through 10.")

    metrics = {year: {} for year in source}
    for query in queries:
        result = db.execute(query.read_text(encoding="utf-8"))
        name = result.description[1][0]
        values = result.fetchall()
        if [year for year, _ in values] != list(source):
            raise ValueError(f"Unexpected report years in {query.name}.")
        for year, value in values:
            metrics[year][name] = value
    return source, metrics


def validate(source, metrics):
    for year, m in metrics.items():
        revenue, customers = source[year]
        if (m["total_revenue"], m["total_customers_current_year"]) != (revenue, customers):
            raise ValueError(f"Current totals do not match the source for {year}.")

        prior = source.get(year - 1)
        if prior is None:
            comparison_values = [value for name, value in m.items()
                                 if name not in ("total_revenue", "total_customers_current_year")]
            if any(value is not None for value in comparison_values):
                raise ValueError(f"Expected empty comparison values for {year}.")
            continue

        prior_revenue, prior_customers = prior
        retained_current = m["existing_customer_revenue_current_year"]
        retained_prior = m["existing_customer_revenue_prior_year"]
        new_revenue = m["new_customer_revenue"]
        attrition = m["revenue_lost_from_attrition"]
        growth = m["existing_customer_growth"]
        checks = [
            ("current-year revenue", revenue == retained_current + new_revenue),
            ("prior-year revenue", prior_revenue == retained_prior + attrition),
            ("retained revenue change", growth == retained_current - retained_prior),
            ("revenue change", revenue - prior_revenue == new_revenue + growth - attrition),
            ("prior-year count", m["total_customers_previous_year"] == prior_customers),
            ("customer change", customers - prior_customers == m["new_customers"] - m["lost_customers"]),
        ]
        failures = [label for label, passed in checks if not passed]
        if failures:
            raise ValueError(f"{year} failed reconciliation: {', '.join(failures)}")


def export_summary(metrics, csv_path):
    fields = list(next(iter(metrics.values())))
    revenue_fields = set(fields[:6])
    with csv_path.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.writer(destination)
        writer.writerow(["report_year", *fields])
        for year, values in metrics.items():
            row = [year]
            for name in fields:
                value = values[name]
                if value is not None and name in revenue_fields:
                    value = f"{Decimal(value) / 100:.2f}"
                row.append(value)
            writer.writerow(row)


def write_notes(source, metrics, notes_path):
    lines = ["# Figures for the case study", "",
             "Revenue is shown in source currency units.", ""]
    for year, (revenue, customers) in source.items():
        lines.extend([f"## {year}", "",
                      f"- Total net revenue: {Decimal(revenue) / 100:,.2f}",
                      f"- Active customers: {customers:,}"])
        prior = source.get(year - 1)
        if prior is None:
            lines.extend(["- Prior-year comparison: N/A", ""])
            continue

        m = metrics[year]
        prior_revenue, prior_count = prior
        change = revenue - prior_revenue
        contributions = {
            "new customer revenue": m["new_customer_revenue"],
            "retained customer growth": m["existing_customer_growth"],
            "attrition impact": -m["revenue_lost_from_attrition"],
        }
        lines.append(f"- Revenue change vs. {year - 1}: {Decimal(change) / 100:+,.2f}")
        if prior_revenue > 0:
            lines.append(f"- Revenue change percentage: {Decimal(change) / prior_revenue:+.1%}")
        for label, value in contributions.items():
            lines.append(f"- {label.capitalize()}: {Decimal(value) / 100:+,.2f}")
        largest = max(map(abs, contributions.values()))
        if largest:
            drivers = [name for name, value in contributions.items() if abs(value) == largest]
            lines.append(f"- Largest contribution by absolute size: {', '.join(drivers)}")
        lines.extend([
            f"- Customer change: {customers - prior_count:+,}",
            f"- New customers: {m['new_customers']:,}",
            f"- Lost customers: {m['lost_customers']:,}",
            "",
        ])
    notes_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="Path to the Stout case study CSV")
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()
    try:
        output_dir = args.out.resolve()
        summary_path = output_dir / "annual_metrics.csv"
        if args.csv_path.resolve() == summary_path:
            raise ValueError("Choose an output path that does not overwrite the input CSV.")
        with closing(sqlite3.connect(":memory:")) as db:
            source, metrics = run_queries(db, args.csv_path)
        validate(source, metrics)
        output_dir.mkdir(parents=True, exist_ok=True)
        export_summary(metrics, summary_path)
        write_notes(source, metrics, output_dir / "findings_notes.md")
    except (OSError, ValueError, sqlite3.Error, csv.Error, OverflowError) as error:
        parser.exit(1, f"Case study error: {error}\n")
    print(f"Reconciled {len(metrics)} reporting years. Outputs: {output_dir}")


if __name__ == "__main__":
    main()
