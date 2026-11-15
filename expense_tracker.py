"""Command-line tool: add, list and summarise expenses.

Examples:
  python expense_tracker.py add 450 food "lunch" --date 2026-10-03
  python expense_tracker.py list
  python expense_tracker.py report --month 2026-10
"""
import argparse
import csv
from datetime import date, datetime

from analytics import (
    COLUMNS, DATA_FILE, build_insights, budget_status,
    category_breakdown, load_expenses, monthly_totals,
)


def parse_amount(value):
    try:
        amount = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Amount must be a number, got '{value}'")
    if amount <= 0:
        raise argparse.ArgumentTypeError("Amount must be greater than zero.")
    return amount


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Date must be YYYY-MM-DD, got '{value}'")


def parse_month(value):
    try:
        return datetime.strptime(value, "%Y-%m").strftime("%Y-%m")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Month must be YYYY-MM, got '{value}'")


def add_expense(amount, category, description, when):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not DATA_FILE.exists() or DATA_FILE.stat().st_size == 0
    with DATA_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if needs_header:
            writer.writerow(COLUMNS)
        writer.writerow([when, f"{amount:.2f}", category.strip().title(), description.strip()])
    print(f"Added: {when} | Rs {amount:.2f} | {category.strip().title()} | {description}")


def show_list():
    df = load_expenses()
    if df.empty:
        print("No expenses recorded yet.")
        return
    view = df.assign(date=df["date"].dt.strftime("%Y-%m-%d"))
    print(view[["date", "amount", "category", "description"]]
          .sort_values("date", ascending=False).to_string(index=False))


def show_report(month=None):
    df = load_expenses()
    if df.empty:
        print("No expenses recorded yet. Run seed_data.py or use the add command.")
        return

    if df.attrs.get("dropped"):
        print(f"Note: skipped {df.attrs['dropped']} row(s) with an invalid date or amount.\n")

    totals = monthly_totals(df)
    month = month or totals.index[-1]
    if month not in totals.index:
        print(f"No expenses for {month}. Months with data: {', '.join(totals.index)}")
        return

    print("=== Monthly totals (Rs) ===")
    print(totals.round(0).to_string())

    by_cat = category_breakdown(df, month)
    print(f"\n=== Category breakdown for {month} (Rs) ===")
    print(by_cat.round(0).to_string())

    print("\n=== Budget check ===")
    print(budget_status(by_cat).to_string(index=False))

    print("\n=== Insights ===")
    for line in build_insights(df, month):
        print(f"- {line}")


def main():
    parser = argparse.ArgumentParser(description="Personal expense tracker")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add an expense")
    p_add.add_argument("amount", type=parse_amount)
    p_add.add_argument("category")
    p_add.add_argument("description", nargs="?", default="")
    p_add.add_argument("--date", type=parse_date, default=None, help="YYYY-MM-DD (default: today)")

    sub.add_parser("list", help="List all expenses")

    p_report = sub.add_parser("report", help="Monthly summary and insights")
    p_report.add_argument("--month", type=parse_month, default=None, help="YYYY-MM (default: latest)")

    args = parser.parse_args()

    if args.command == "add":
        when = args.date or date.today().isoformat()
        add_expense(args.amount, args.category, args.description, when)
    elif args.command == "list":
        show_list()
    elif args.command == "report":
        show_report(args.month)


if __name__ == "__main__":
    main()