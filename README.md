# Personal Finance Tracker

A Python tool to record personal expenses, analyse monthly spending, and view
results in an interactive dashboard with automatic insights.

## Features
- Add, list and summarise expenses from the command line
- Load and clean any expense CSV (invalid rows are skipped and reported)
- Monthly totals, month-over-month change, category breakdown
- Budget tracking per category with over-budget alerts
- Streamlit dashboard with KPIs, charts, insights and CSV export

## Setup

Requires Python 3.10 or newer.

**Mac / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python seed_data.py                    # create sample data (Aug-Oct 2026)
python expense_tracker.py report --month 2026-10
streamlit run dashboard.py             # opens http://localhost:8501
```

## Data format

`data/expenses.csv` with the columns `date,amount,category,description`.
Dates use `YYYY-MM-DD`. You can also upload any CSV with these columns in the dashboard.

## About the data

The sample data is **simulated** using random generation with a fixed seed,
with a 15% increase in October to illustrate a trend. Real personal spending
is not included. [Optional: add a sentence about any days of real logged spending.]

## Limitations
- Single user, three months of data, no income or savings data
- Budgets are set manually and are not learned from history
- Insights are rule-based summaries, not forecasts