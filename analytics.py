"""Shared data loading, cleaning and analysis used by the CLI and the dashboard."""
from pathlib import Path

import csv
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "expenses.csv"
COLUMNS = ["date", "amount", "category", "description"]

# Monthly budget per category (Rs). Change these in the dashboard sidebar too.
DEFAULT_BUDGETS = {"Food": 5000, "Transport": 2000, "Shopping": 3000, "Bills": 4000, "Other": 1000}


def clean_expenses(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalise any expense table: fix column names and types, drop unusable rows."""
    df = raw.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[COLUMNS].copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["category"] = (
        df["category"].fillna("").astype(str).str.strip().str.title().replace("", "Other")
    )
    df["description"] = df["description"].fillna("").astype(str).str.strip()

    unusable = df["date"].isna() | df["amount"].isna()
    dropped = int(unusable.sum())
    df = df[~unusable].copy()
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df = df.sort_values("date").reset_index(drop=True)
    df.attrs["dropped"] = dropped
    return df


def load_expenses(path: Path = DATA_FILE) -> pd.DataFrame:
    """Load the expense CSV. A missing or empty file returns an empty, valid table."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return clean_expenses(pd.DataFrame(columns=COLUMNS))
    return clean_expenses(pd.read_csv(path))


def monthly_totals(df: pd.DataFrame) -> pd.Series:
    """Total spend per month, indexed by 'YYYY-MM' in chronological order."""
    return df.groupby("month")["amount"].sum().sort_index()


def category_breakdown(df: pd.DataFrame, month: str) -> pd.Series:
    """Spend per category for one month, largest first."""
    sub = df[df["month"] == month]
    return sub.groupby("category")["amount"].sum().sort_values(ascending=False)


def budget_status(by_cat: pd.Series, budgets: dict | None = None) -> pd.DataFrame:
    """Compare category spend against budgets: OK, Near limit (90%+), or Over budget."""
    budgets = budgets or DEFAULT_BUDGETS
    rows = []
    for cat, limit in budgets.items():
        spent = float(by_cat.get(cat, 0.0))
        pct = (spent / limit * 100) if limit else 0.0
        if spent > limit:
            status = "Over budget"
        elif pct >= 90:
            status = "Near limit"
        else:
            status = "OK"
        rows.append({
            "Category": cat,
            "Spent (Rs)": round(spent),
            "Budget (Rs)": limit,
            "Used %": round(pct, 1),
            "Status": status,
        })
    return pd.DataFrame(rows)


def build_insights(df: pd.DataFrame, month: str, budgets: dict | None = None) -> list[str]:
    """Plain-English findings for one month."""
    budgets = budgets or DEFAULT_BUDGETS
    totals = monthly_totals(df)
    by_cat = category_breakdown(df, month)
    total = float(by_cat.sum())
    if total == 0:
        return ["No spending recorded for this month."]

    insights = []
    top_cat = by_cat.index[0]
    top_amt = float(by_cat.iloc[0])
    insights.append(
        f"{top_cat} is the largest category at Rs {top_amt:,.0f}, "
        f"which is {top_amt / total * 100:.0f}% of the month's spend."
    )

    months = list(totals.index)
    pos = months.index(month)
    if pos > 0:
        prev = months[pos - 1]
        prev_total = float(totals[prev])
        if prev_total:
            change = (float(totals[month]) - prev_total) / prev_total * 100
            direction = "up" if change >= 0 else "down"
            insights.append(
                f"Total spend is {direction} {abs(change):.0f}% versus {prev} "
                f"(Rs {totals[month]:,.0f} vs Rs {prev_total:,.0f})."
            )

    status = budget_status(by_cat, budgets)
    over = status[status["Status"] == "Over budget"]
    for _, row in over.iterrows():
        excess = row["Spent (Rs)"] - row["Budget (Rs)"]
        insights.append(f"{row['Category']} is over budget by Rs {excess:,.0f}.")
    if over.empty:
        insights.append("All categories are within budget.")

    insights.append(
        f"Average monthly spend across {len(totals)} month(s) is Rs {totals.mean():,.0f}."
    )

    sub = df[df["month"] == month]
    big = sub.loc[sub["amount"].idxmax()]
    desc = big["description"] or "no description"
    insights.append(
        f"Largest single expense: Rs {big['amount']:,.0f} on {big['category']} "
        f"({desc}) on {big['date'].strftime('%d %b')}."
    )
    return insights
def category_change(df: pd.DataFrame, month: str) -> pd.DataFrame:
    """Spend per category for a month versus the previous month."""
    months = list(monthly_totals(df).index)
    if month not in months or months.index(month) == 0:
        return pd.DataFrame(columns=["Category", "Previous (Rs)", "Current (Rs)", "Change %"])
    prev = months[months.index(month) - 1]
    combined = pd.DataFrame({
        "Previous (Rs)": category_breakdown(df, prev),
        "Current (Rs)": category_breakdown(df, month),
    }).fillna(0)
    base = combined["Previous (Rs)"].replace(0, float("nan"))
    combined["Change %"] = ((combined["Current (Rs)"] - combined["Previous (Rs)"]) / base * 100).round(1)
    combined = combined.reset_index().rename(columns={"index": "Category", "category": "Category"})
    combined[["Previous (Rs)", "Current (Rs)"]] = combined[["Previous (Rs)", "Current (Rs)"]].round(0)
    return combined.sort_values("Current (Rs)", ascending=False).reset_index(drop=True)


def add_expense_row(amount, category, description, when):
    """Append one expense to the CSV, creating the file and header if needed."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not DATA_FILE.exists() or DATA_FILE.stat().st_size == 0
    with DATA_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if needs_header:
            writer.writerow(COLUMNS)
        writer.writerow([when, f"{float(amount):.2f}", str(category).strip().title(), str(description).strip()])