"""Generate realistic sample expenses for Aug-Oct 2026.

Usage:
  python seed_data.py            # does nothing if data already exists
  python seed_data.py --force    # overwrite existing data
"""
import csv
import random
import sys
from datetime import date, timedelta

from analytics import COLUMNS, DATA_FILE

# category: ((min, max) amount, average entries per week, sample descriptions)
PATTERNS = {
    "Food":      ((80, 450),    4,   ["lunch", "groceries", "dinner out", "snacks", "chai and samosa"]),
    "Transport": ((30, 200),    3,   ["auto", "metro", "cab to college", "fuel"]),
    "Shopping":  ((200, 1500),  0.5, ["clothes", "stationery", "online order", "toiletries"]),
    "Bills":     ((400, 1200),  0.3, ["mobile recharge", "electricity", "wifi", "subscription"]),
    "Other":     ((50, 400),    0.5, ["medicine", "gift", "photocopy", "donation"]),
}


def main():
    force = "--force" in sys.argv
    if DATA_FILE.exists() and DATA_FILE.stat().st_size > 0 and not force:
        print(f"{DATA_FILE} already has data. Run with --force to regenerate it.")
        return

    random.seed(42)  # same data on every run, so report numbers stay consistent
    rows = []
    day = date(2026, 8, 1)
    end = date(2026, 10, 31)
    while day <= end:
        # Simulate a spending increase in October so the trend is visible
        factor = 1.15 if day.month == 10 else 1.0
        for category, ((low, high), per_week, descriptions) in PATTERNS.items():
            if random.random() < per_week / 7:
                amount = random.uniform(low, high) * factor
                rows.append([day.isoformat(), f"{amount:.2f}", category, random.choice(descriptions)])
        day += timedelta(days=1)

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    print(f"Wrote {len(rows)} sample expenses to {DATA_FILE}")


if __name__ == "__main__":
    main()