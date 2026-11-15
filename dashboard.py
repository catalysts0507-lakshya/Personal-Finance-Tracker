"""Personal Finance Dashboard. Run with: python -m streamlit run dashboard.py"""
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from analytics import (
    COLUMNS, DATA_FILE, DEFAULT_BUDGETS, add_expense_row, build_insights,
    budget_status, category_breakdown, category_change, clean_expenses,
    load_expenses, monthly_totals,
)

TEMPLATE_CSV = "date,amount,category,description\n2026-10-01,450,Food,lunch\n2026-10-02,120,Transport,auto\n"
ACCENT = "#2563eb"

st.set_page_config(page_title="Personal Finance Dashboard", page_icon="💰", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #e8f0fe 0%, #f5f0ff 50%, #fff4e6 100%);
    }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.92);
        border-radius: 16px;
        padding: 16px 20px;
        box-shadow: 0 6px 18px rgba(31, 41, 55, 0.08);
    }
    section[data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.75);
    }
    h1, h2, h3 { color: #1f2a44; }
    p, li, label, [data-testid="stMarkdownContainer"] { color: #111827; }
    [data-testid="stCaptionContainer"] { color: #374151 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("💰 Personal Finance Dashboard")


def clean_chart(chart):
    """Transparent chart background with darker, more readable text."""
    return (
        chart.configure(background="transparent")
        .configure_view(strokeWidth=0, fill="transparent")
        .configure_axis(
            labelColor="#111827", titleColor="#111827",
            labelFontWeight=600, titleFontWeight=600, labelFontSize=12,
            gridColor="rgba(100, 116, 139, 0.25)", domainColor="rgba(100, 116, 139, 0.5)",
        )
        .configure_legend(labelColor="#111827", titleColor="#111827", labelFontWeight=600)
    )


def add_expense_form():
    with st.expander("➕ Add an expense (saves to your sample data file)"):
        with st.form("add_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            amount = c1.number_input("Amount (Rs)", min_value=1.0, step=10.0)
            category = c2.selectbox("Category", list(DEFAULT_BUDGETS))
            when = c3.date_input("Date", value=date.today())
            description = st.text_input("Description")
            if st.form_submit_button("Save expense"):
                add_expense_row(amount, category, description, when.isoformat())
                st.rerun()


# ---- Data source (sidebar) ----
with st.sidebar:
    st.header("Data source")
    choice = st.radio("Use", ["Sample data", "Upload my CSV"], horizontal=True)
    uploaded = None
    if choice == "Upload my CSV":
        uploaded = st.file_uploader("Expense CSV", type=["csv"])
        st.caption("Columns: date, amount, category, description")
    st.download_button("Download CSV template", TEMPLATE_CSV, "expense_template.csv", "text/csv")

if choice == "Upload my CSV":
    if uploaded is None:
        st.info("Upload a CSV in the sidebar to build your report. Download the template if you're not sure of the format.")
        st.stop()
    try:
        df = clean_expenses(pd.read_csv(uploaded))
    except Exception as exc:
        st.error(f"Could not read this file: {exc}")
        st.stop()
    source = f"uploaded file: {uploaded.name}"
else:
    add_expense_form()
    df = load_expenses()
    source = f"data/{DATA_FILE.name}"

if df.empty:
    st.info("No expense data found. Run `python seed_data.py` or add an expense above.")
    st.stop()

if df.attrs.get("dropped"):
    st.warning(f"{df.attrs['dropped']} row(s) had an invalid date or amount and were skipped.")

totals = monthly_totals(df)
months = list(totals.index)
categories = sorted(df["category"].unique())

with st.sidebar:
    st.header("Filters")
    selected = st.selectbox("Month", months, index=len(months) - 1)
    with st.expander("Monthly budgets (Rs)", expanded=True):
        budgets = {
            cat: st.number_input(cat, min_value=0, value=DEFAULT_BUDGETS.get(cat, 2000),
                                 step=500, key=f"budget_{cat}")
            for cat in categories
        }

by_cat = category_breakdown(df, selected)
month_total = float(by_cat.sum())
month_rows = df[df["month"] == selected]
pos = months.index(selected)

st.caption(f"Data source: {source}")

# ---- KPI tiles ----
k1, k2, k3, k4 = st.columns(4)
if pos > 0:
    prev_month = months[pos - 1]
    prev_total = float(totals[prev_month])
    change = (month_total - prev_total) / prev_total * 100 if prev_total else None
else:
    prev_month, change = None, None

if change is not None:
    k1.metric(f"Spend in {selected}", f"Rs {month_total:,.0f}",
              delta=f"{change:+.0f}% vs {prev_month}", delta_color="inverse")
else:
    k1.metric(f"Spend in {selected}", f"Rs {month_total:,.0f}")
k2.metric("Transactions", len(month_rows))
k3.metric("Avg per transaction",
          f"Rs {month_rows['amount'].mean():,.0f}" if len(month_rows) else "-")
k4.metric("Total tracked (all months)", f"Rs {df['amount'].sum():,.0f}")

# ---- Shared data for charts ----
heat = df.groupby(["category", "month"], as_index=False)["amount"].sum()
heat_order = list(df.groupby("category")["amount"].sum().sort_values(ascending=False).index)
cat_colors = alt.Scale(scheme="tableau10", domain=heat_order)

# Full grid (zeros filled) so the ribbon has no gaps
ribbon_df = (
    df.pivot_table(index="month", columns="category", values="amount",
                   aggfunc="sum", fill_value=0)
    .stack().rename("amount").reset_index()
)

totals_df = totals.rename("Total").reset_index().rename(columns={"month": "Month"})
line_chart = (
    alt.Chart(totals_df)
    .mark_line(point=alt.OverlayMarkDef(size=80, filled=True), color=ACCENT, strokeWidth=3)
    .encode(
        x=alt.X("Month:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Total:Q", title="Rs"),
        tooltip=["Month", alt.Tooltip("Total:Q", format=",.0f", title="Rs")],
    )
    .properties(height=300)
)

share_df = by_cat.rename("Amount").reset_index().rename(columns={"category": "Category"})
donut = (
    alt.Chart(share_df)
    .mark_arc(innerRadius=70, outerRadius=130, cornerRadius=4, padAngle=0.012)
    .encode(
        theta=alt.Theta("Amount:Q"),
        color=alt.Color("Category:N", scale=cat_colors,
                        legend=alt.Legend(title=None, orient="right")),
        tooltip=["Category", alt.Tooltip("Amount:Q", format=",.0f", title="Rs")],
    )
    .properties(height=300)
)

ribbon = (
    alt.Chart(ribbon_df)
    .mark_area(interpolate="monotone", opacity=0.9)
    .encode(
        x=alt.X("month:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("amount:Q", stack="center", axis=None),
        color=alt.Color("category:N", scale=cat_colors,
                        legend=alt.Legend(title="Category", orient="right")),
        tooltip=["category", "month", alt.Tooltip("amount:Q", format=",.0f", title="Rs")],
    )
    .properties(height=340)
)

heatmap = (
    alt.Chart(heat)
    .mark_rect(cornerRadius=4)
    .encode(
        x=alt.X("month:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("category:N", sort=heat_order, title=None),
        color=alt.Color("amount:Q", scale=alt.Scale(range=["#eef4ff", ACCENT]), legend=alt.Legend(title="Rs")),
        tooltip=["category", "month", alt.Tooltip("amount:Q", format=",.0f", title="Rs")],
    )
    .properties(height=max(260, 28 * len(heat_order)))
)

# ---- Charts ----
st.subheader("Spending over time")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Total spend by month**")
    st.altair_chart(clean_chart(line_chart), use_container_width=True)
with c2:
    st.markdown(f"**Where the money went, {selected}**")
    st.altair_chart(clean_chart(donut), use_container_width=True)

st.markdown("**Category flow across months**")
st.altair_chart(clean_chart(ribbon), use_container_width=True)

st.markdown("**Category heatmap: darker means more spent**")
st.altair_chart(clean_chart(heatmap), use_container_width=True)

# ---- Month-over-month by category ----
st.subheader(f"What changed in {selected}")
mom = category_change(df, selected)
if mom.empty:
    st.caption("No earlier month to compare against.")
else:
    st.dataframe(mom, hide_index=True)

# ---- Budget check (colour-coded) ----
st.subheader(f"Budget check for {selected}")
status = budget_status(by_cat, budgets)


def colour_status(row):
    colours = {"Over budget": "#ffd6d6", "Near limit": "#fff3c4", "OK": "#dff5e1"}
    return [f"background-color: {colours.get(row['Status'], '')}"] * len(row)


st.dataframe(
    status.style.apply(colour_status, axis=1).format({"Used %": "{:.1f}%"}),
    hide_index=True,
)

# ---- Insights ----
st.subheader("Key insights")
for line in build_insights(df, selected, budgets):
    st.markdown(f"- {line}")

# ---- Transactions and export ----
st.subheader(f"Transactions in {selected}")
table = (month_rows.assign(date=month_rows["date"].dt.strftime("%Y-%m-%d"))
         [["date", "category", "description", "amount"]]
         .sort_values("date", ascending=False))
st.dataframe(table, hide_index=True)

st.download_button(
    "Download cleaned data as CSV",
    df[COLUMNS].to_csv(index=False),
    file_name="expenses_clean.csv",
    mime="text/csv",
)