"""Streamlit front end: executive dashboard, deep dives, copilot, governance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

st.set_page_config(page_title="Retail Analytics", page_icon="🛒", layout="wide")

from retail import analytics, audit  # noqa: E402
from retail.config import QUALITY_REPORT_PATH, WAREHOUSE_PATH  # noqa: E402
from retail.sql_guard import SQLValidationError, execute_readonly_query  # noqa: E402

TEAL, AMBER, SLATE = "#0F766E", "#D97706", "#475569"
st.markdown(
    """<style>
    .block-container {padding-top: 1.6rem; max-width: 1300px;}
    [data-testid="stMetricValue"] {font-size: 1.6rem;}
    .note {color: #475569; font-size: 0.92rem;}
    </style>""",
    unsafe_allow_html=True,
)

if not WAREHOUSE_PATH.exists():
    st.error("Warehouse not built. Run `python -m retail.pipeline` first.")
    st.stop()


@st.cache_data(show_spinner=False)
def run(key: str) -> pd.DataFrame:
    return analytics.run_analysis(key)


@st.cache_data(show_spinner=False)
def stats() -> dict:
    return analytics.load_stats()


@st.cache_data(show_spinner=False)
def findings() -> list[str]:
    return analytics.headline_findings()


def chart(fig, height: int = 360):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=10, r=10, t=50, b=10),
                      title_font_size=15)
    st.plotly_chart(fig, use_container_width=True)


def md(text: str) -> str:
    """Escape $ so Streamlit does not render currency pairs as LaTeX."""
    return text.replace("$", "\\$")


def note(text: str) -> None:
    st.markdown(f'<p class="note">{text}</p>', unsafe_allow_html=True)


# --- pages ----------------------------------------------------------------------

def overview() -> None:
    kpi = analytics.kpi_summary()
    st.subheader("Q4 2017 vs Q3 2017")
    cards = [("Net sales", "net_sales", lambda v: f"${v / 1e6:,.2f}M", "%"),
             ("Baskets", "baskets", lambda v: f"{v:,.0f}", "%"),
             ("Avg basket", "avg_basket_value", lambda v: f"${v:,.2f}", "%"),
             ("Households", "households", lambda v: f"{v:,.0f}", "%"),
             ("Discount rate", "discount_rate_pct", lambda v: f"{v:.1f}%", " pts"),
             ("Own-brand share", "private_label_share_pct", lambda v: f"{v:.1f}%", " pts")]
    for col, (label, key, fmt, unit) in zip(st.columns(len(cards)), cards, strict=True):
        item = kpi[key]
        col.metric(label, fmt(item["current"]), f"{item['delta']:+.1f}{unit}",
                   delta_color="inverse" if key == "discount_rate_pct" else "normal",
                   help=f"Q3: {fmt(item['prior'])}")
    with st.expander("Headline findings", expanded=True):
        for f in findings():
            st.markdown(f"- {md(f)}")
    weekly = run("weekly_trend")
    weekly = weekly[weekly.retail_week.between(2, 52)]
    fig = px.bar(weekly, x="week_start", y="net_sales", title="Weekly merchandise sales (full weeks)",
                 color_discrete_sequence=[TEAL], hover_data=["holidays", "wow_growth_pct"])
    fig.add_scatter(x=weekly.week_start, y=weekly.rolling_4w_sales, name="4-week average",
                    line=dict(color=AMBER))
    chart(fig)
    left, right = st.columns(2)
    dept = run("department_performance").head(10)
    with left:
        chart(px.bar(dept, x="net_sales", y="department", orientation="h", color="discount_rate_pct",
                     color_continuous_scale="Teal", title="Top departments (colour = discount rate %)")
              .update_yaxes(categoryorder="total ascending"))
    with right:
        st.markdown("**Department scorecard**")
        st.dataframe(dept, hide_index=True, use_container_width=True)


def customers() -> None:
    left, right = st.columns(2)
    with left:
        rfm = run("rfm_segments")
        chart(px.bar(rfm, x="segment", y="sales_share_pct", text="households",
                     title="RFM segments: share of sales (label = households)",
                     color_discrete_sequence=[TEAL]))
    with right:
        conc = run("customer_concentration")
        fig = px.bar(conc, x="decile", y="sales_share_pct", title="Sales share by household decile",
                     color_discrete_sequence=[TEAL])
        fig.add_scatter(x=conc.decile, y=conc.cumulative_share_pct, name="Cumulative %",
                        line=dict(color=AMBER))
        chart(fig)
    deal = run("discount_dependency")
    chart(px.bar(deal, x="deal_segment", y=["sales_share_pct"], text="households",
                 title="Deal dependence: share of sales by segment (label = households)",
                 color_discrete_sequence=[SLATE]), height=320)
    st.markdown("**Spend by income and household type** (801 surveyed households)")
    demo = run("demographic_spend")
    pivot = demo.pivot(index="income_band", columns="household_comp", values="avg_annual_sales")
    pivot = pivot.reindex(["Under 35K", "35-74K", "75-124K", "125K+"])
    chart(px.imshow(pivot, text_auto=".0f", color_continuous_scale="Teal", aspect="auto",
                    title="Average annual spend ($)"), height=340)
    left, right = st.columns(2)
    with left:
        st.markdown("**When households shop** (store-local time)")
        pat = run("shopping_patterns")
        chart(px.density_heatmap(pat, x="day_name", y="daypart", z="avg_basket_value",
                                 histfunc="avg", text_auto=".2f", color_continuous_scale="Teal",
                                 category_orders={"day_name": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]},
                                 title="Average basket value ($)"), height=320)
    with right:
        st.markdown("**Bought together** (category affinity)")
        st.dataframe(run("market_basket").head(10), hide_index=True, use_container_width=True)


def campaigns() -> None:
    s = stats()
    st.markdown("**Coupon redemptions by households already buying the product** (56-day look-back)")
    if "coupon_habitual" in s:
        cols = st.columns(4)
        for col, (k, v) in zip(cols, s["coupon_habitual"].items(), strict=False):
            col.metric(k, f"{v['habitual_pct']:.1f}%",
                       help=f"95% CI {v['ci95_pct'][0]}-{v['ci95_pct'][1]}%, n={v['redemptions']:,}")
    st.dataframe(run("campaign_reach"), hide_index=True, use_container_width=True)
    if "campaign_did" in s:
        st.markdown("**Campaign impact test: difference-in-differences with a placebo check**")
        rows = []
        for ctype, r in s["campaign_did"].items():
            for test in ("did", "placebo"):
                x = r[test]
                rows.append({"campaign_type": ctype,
                             "test": "Launch effect" if test == "did" else "Placebo (pre-launch)",
                             "effect_$_per_household_week": x["effect_per_household_week"],
                             "ci_low": x["ci95"][0], "ci_high": x["ci95"][1],
                             "p_value": round(x["p_value"], 4)})
        did = pd.DataFrame(rows)
        fig = px.scatter(did, x="effect_$_per_household_week", y="campaign_type", color="test",
                         title="Effect on weekly spend ($), 95% CI",
                         color_discrete_sequence=[TEAL, AMBER])
        fig.update_traces(marker_size=12)
        for row in did.itertuples():
            fig.add_shape(type="line", x0=row.ci_low, x1=row.ci_high, y0=row.campaign_type,
                          y1=row.campaign_type, line=dict(color=TEAL if row.test == "Launch effect" else AMBER))
        fig.add_vline(x=0, line_dash="dot", line_color=SLATE)
        chart(fig, height=300)
        st.dataframe(did, hide_index=True, use_container_width=True)
        note("A significant placebo means targeted households were already trending differently "
             "before launch, so the launch effect is not a causal estimate. Recommendation: hold "
             "out a random 10% of every target list.")


def promotions() -> None:
    s = stats().get("promotion_lift", {})
    if s:
        lift = pd.DataFrame([{"promotion": k, "lift_pct": v["lift_pct"], "ci_low": v["ci95_pct"][0],
                              "ci_high": v["ci95_pct"][1], "pairs": v["pairs"]} for k, v in s.items()])
        chart(px.bar(lift, x="promotion", y="lift_pct", text="lift_pct",
                     error_y=lift.ci_high - lift.lift_pct, error_y_minus=lift.lift_pct - lift.ci_low,
                     title="Sales lift vs the same product x store in unpromoted weeks (%)",
                     color_discrete_sequence=[TEAL]), height=340)
        note("Promotions are not randomly assigned, so treat lift as an upper bound.")
    st.markdown("**Own-brand opportunity**: large categories, private-label share and price gap")
    st.dataframe(run("private_label_gap"), hide_index=True, use_container_width=True)


def ask_page() -> None:
    from retail.copilot import ask

    note("Answers come from the governed SQL library, the metric layer and the documentation. "
         "Every answer lists its sources and is written to the audit log.")
    examples = ["Are coupons incremental?", "Top 10 products in Q4", "Which categories are bought together?",
                "Do campaigns have an impact on spend?", "How is gross sales defined?",
                "Sales in the MEAT department in Q3"]
    choice = st.selectbox("Try an example", [""] + examples)
    question = st.text_input("Your question", value=choice)
    if question:
        with st.spinner("Thinking"):
            result = ask(question)
        st.markdown(md(result.answer))
        st.caption(f"Route: {result.route} · mode: {result.mode} · {result.latency_ms} ms")
        if result.sql:
            with st.expander("SQL that ran"):
                st.code(result.sql, language="sql")


def sql_runner() -> None:
    note("Read-only, governed SQL. One SELECT, no file access, row-capped.")
    library = {a.title: a.sql for a in analytics.list_analyses()}
    pick = st.selectbox("Start from the analysis library", list(library))
    sql = st.text_area("SQL", library[pick], height=300, key=f"sql-{pick}")
    if st.button("Run", type="primary"):
        try:
            res = execute_readonly_query(sql, max_rows=1000)
            df = pd.DataFrame(res.rows, columns=res.columns)
            st.caption(f"{res.row_count:,} rows" + (" (truncated)" if res.truncated else ""))
            st.dataframe(df, hide_index=True, use_container_width=True)
            st.download_button("Download CSV", df.to_csv(index=False), "query.csv", "text/csv")
        except SQLValidationError as exc:
            st.error(f"Blocked: {exc}")
        except Exception as exc:
            st.error(f"Query failed: {exc}")


def quality() -> None:
    report = json.loads(QUALITY_REPORT_PATH.read_text(encoding="utf-8"))
    checks = pd.DataFrame(report["checks"])
    a, b, c = st.columns(3)
    a.metric("Checks passed", f"{report['passed']}/{report['total']}")
    b.metric("Blocking checks", int((checks.severity == "error").sum()))
    c.metric("Documented warnings", int(((checks.severity == "warn") & (checks.violations > 0)).sum()))
    checks["status"] = checks.apply(lambda r: "✅" if r.passed and not (r.severity == "warn" and r.violations)
                                    else ("⚠️" if r.passed else "❌"), axis=1)
    st.dataframe(checks[["status", "name", "severity", "violations", "description"]],
                 hide_index=True, use_container_width=True)


def audit_page() -> None:
    events = audit.read_recent(200)
    if not events:
        st.info("No questions asked yet.")
        return
    df = pd.DataFrame(events)
    a, b, c = st.columns(3)
    a.metric("Questions", len(df))
    b.metric("Median latency", f"{int(df.latency_ms.median())} ms")
    c.metric("Errors", int(df.error.notna().sum()))
    st.dataframe(df, hide_index=True, use_container_width=True)


st.title("Retail Analytics: Complete Journey 2017")
note("1.46M real grocery transactions from 2,469 households (84.51° / dunnhumby). "
     "Merchandise only: fuel and gift cards excluded.")
pages = {"Overview": overview, "Customers": customers, "Campaigns & coupons": campaigns,
         "Promotions & pricing": promotions, "Ask the data": ask_page, "SQL runner": sql_runner,
         "Data quality": quality, "Audit log": audit_page}
for tab, render in zip(st.tabs(list(pages)), pages.values(), strict=True):
    with tab:
        render()
