"""Reconcile Power BI (DAX) measure values against independent SQL.

reports/powerbi_dax_results.json holds values returned by the live Power BI
model. This module recomputes each one in SQL against the warehouse and writes
reports/reconciliation.md. tests/test_reconciliation.py fails if any value
drifts, so a stale or wrong dashboard number cannot go unnoticed.

    python -m retail.reconcile
"""

from __future__ import annotations

import json
import math

from retail.analytics import load_stats, run_analysis
from retail.config import REPORTS_DIR
from retail.sql_guard import execute_readonly_query

DAX_PATH = REPORTS_DIR / "powerbi_dax_results.json"
OUT_PATH = REPORTS_DIR / "reconciliation.md"
TOLERANCE = 1e-6  # relative


def _one(sql: str) -> dict:
    return execute_readonly_query(sql).rows[0]


def sql_values() -> dict[str, float]:
    """Every value computed in SQL, keyed like the DAX results."""
    out: dict[str, float] = {}
    t = _one("""
        SELECT SUM(s.sales_value) AS net_sales, COUNT(DISTINCT s.basket_id) AS baskets,
               COUNT(DISTINCT s.household_id) AS households,
               SUM(s.retail_disc + s.coupon_match_disc) / SUM(s.gross_sales) AS discount_rate,
               SUM(CASE WHEN p.brand = 'Private' THEN s.sales_value END) / SUM(s.sales_value) AS pl,
               SUM(CASE WHEN s.retail_disc > 0 THEN s.sales_value END) / SUM(s.sales_value) AS promo
        FROM fct_sales s JOIN dim_product p USING (product_id) WHERE s.is_merch""")
    repeat = _one("""SELECT AVG(CASE WHEN n >= 2 THEN 1.0 ELSE 0 END) AS r FROM
                     (SELECT household_id, COUNT(DISTINCT basket_id) n FROM fct_sales WHERE is_merch GROUP BY 1)""")
    coupons = _one("SELECT COUNT(*) FILTER (WHERE is_scored) AS scored, "
                   "COUNT(*) FILTER (WHERE is_scored AND is_habitual) AS habitual FROM mart_coupon_redemptions")
    # Same rule as 07_customer_concentration.sql decile 1 (rank <= 10% of households), unrounded.
    top10 = _one("""
        WITH r AS (SELECT household_id, SUM(sales_value) AS s,
                          ROW_NUMBER() OVER (ORDER BY SUM(sales_value) DESC) AS rk, COUNT(*) OVER () AS n
                   FROM fct_sales WHERE is_merch GROUP BY household_id)
        SELECT SUM(CASE WHEN rk <= 0.1 * n THEN s END) / SUM(s) AS share FROM r""")
    out |= {
        "total/Net Sales": t["net_sales"], "total/Baskets": t["baskets"], "total/Households": t["households"],
        "total/Avg Basket Value": t["net_sales"] / t["baskets"], "total/Discount Rate %": t["discount_rate"],
        "total/Private Label Share %": t["pl"], "total/Promo Sales Share %": t["promo"],
        "total/Top 10% Household Share": top10["share"],
        "total/Repeat Household Rate %": repeat["r"],
        "total/Baskets per Household": t["baskets"] / t["households"],
        "total/Scored Redemptions": coupons["scored"], "total/Habitual Redemptions": coupons["habitual"],
        "total/Habitual Redemption %": coupons["habitual"] / coupons["scored"],
    }
    q = run_analysis("kpi_by_quarter").set_index("quarter")
    q_exact = execute_readonly_query("""
        SELECT d.quarter_name, SUM(s.sales_value) AS sales, COUNT(DISTINCT s.basket_id) AS baskets
        FROM fct_sales s JOIN dim_date d ON d.date_key = s.business_date
        WHERE s.is_merch GROUP BY 1""").rows
    qd = {r["quarter_name"]: r for r in q_exact}
    q3, q4 = qd["Q3 2017"], qd["Q4 2017"]
    out |= {
        "q4/Net Sales": q4["sales"],
        "q4/Net Sales QoQ %": q4["sales"] / q3["sales"] - 1,
        "q4/Avg Basket QoQ %": (q4["sales"] / q4["baskets"]) / (q3["sales"] / q3["baskets"]) - 1,
    }
    assert len(q) == 4
    for row in execute_readonly_query("""
            SELECT g.rfm_segment, COUNT(*) AS households, SUM(g.annual_sales) AS sales,
                   SUM(g.annual_sales) / SUM(SUM(g.annual_sales)) OVER () AS share
            FROM (SELECT m.rfm_segment, m.household_id, SUM(s.sales_value) AS annual_sales
                  FROM mart_household_segments m JOIN fct_sales s USING (household_id)
                  WHERE s.is_merch GROUP BY 1, 2) g GROUP BY 1""").rows:
        out[f"rfm_segment/{row['rfm_segment']}/Households"] = row["households"]
        out[f"rfm_segment/{row['rfm_segment']}/Segment Sales Share %"] = row["share"]
    for row in execute_readonly_query("""
            SELECT deal_segment, COUNT(*) AS households,
                   SUM(annual_sales) / SUM(SUM(annual_sales)) OVER () AS share
            FROM mart_household_segments WHERE deal_segment IS NOT NULL GROUP BY 1""").rows:
        out[f"deal_segment/{row['deal_segment']}/Households"] = row["households"]
        out[f"deal_segment/{row['deal_segment']}/Segment Sales Share %"] = row["share"]
    for row in execute_readonly_query("""
            SELECT campaign_type, AVG(CASE WHEN is_habitual THEN 1.0 ELSE 0 END) AS h
            FROM mart_coupon_redemptions WHERE is_scored GROUP BY 1""").rows:
        out[f"habitual_by_type/{row['campaign_type']}"] = row["h"]
    for row in execute_readonly_query("""
            SELECT p.department, SUM(s.sales_value) AS sales,
                   COUNT(DISTINCT s.household_id) / (SELECT COUNT(*) FROM dim_household)::DOUBLE AS pen,
                   SUM(CASE WHEN p.brand = 'Private' THEN s.sales_value END) / SUM(s.sales_value) AS pl,
                   SUM(s.retail_disc + s.coupon_match_disc) / SUM(s.gross_sales) AS disc
            FROM fct_sales s JOIN dim_product p USING (product_id) WHERE s.is_merch GROUP BY 1""").rows:
        d = row["department"]
        out |= {f"department/{d}/Net Sales": row["sales"], f"department/{d}/Product Penetration %": row["pen"],
                f"department/{d}/Private Label Share %": row["pl"] or 0.0,
                f"department/{d}/Discount Rate %": row["disc"]}
    for k, v in load_stats().get("promotion_lift", {}).items():
        out[f"promotion_lift/{k}"] = v["lift_pct"] / 100
    return out


def _flatten(d: dict, prefix: str = "") -> dict[str, float]:
    flat = {}
    for k, v in d.items():
        if k.startswith("_"):
            continue
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            flat |= _flatten(v, f"{key}/")
        else:
            flat[key] = v
    return flat


def reconcile() -> list[dict]:
    dax = _flatten(json.loads(DAX_PATH.read_text(encoding="utf-8")))
    sql = sql_values()
    rows = []
    for key, dax_value in dax.items():
        sql_value = sql.get(key)
        ok = sql_value is not None and math.isclose(
            float(dax_value), float(sql_value), rel_tol=TOLERANCE, abs_tol=1e-9)
        rows.append({"check": key, "dax": dax_value, "sql": sql_value, "match": ok})
    return rows


def _fmt(v) -> str:
    if v is None:
        return "missing"
    v = float(v)
    return f"{v:,.0f}" if v.is_integer() or abs(v) >= 1000 else f"{v:.6f}"


def write() -> list[dict]:
    rows = reconcile()
    passed = sum(r["match"] for r in rows)
    lines = [
        "# Power BI to SQL reconciliation", "",
        f"**{passed} of {len(rows)} values match** (relative tolerance {TOLERANCE:g}).", "",
        "DAX values come from the live Power BI model (`reports/powerbi_dax_results.json`). SQL values are "
        "recomputed independently against the DuckDB warehouse by `python -m retail.reconcile`. "
        "`tests/test_reconciliation.py` repeats the check on every test run.", "",
        "| Check | DAX (Power BI) | SQL (DuckDB) | Match |", "| --- | ---: | ---: | :---: |",
    ]
    lines += [f"| {r['check']} | {_fmt(r['dax'])} | {_fmt(r['sql'])} | {'yes' if r['match'] else '**NO**'} |"
              for r in rows]
    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def main() -> None:
    rows = write()
    bad = [r for r in rows if not r["match"]]
    print(f"{len(rows) - len(bad)}/{len(rows)} match. Report: {OUT_PATH}")
    for r in bad:
        print("  MISMATCH", r)


if __name__ == "__main__":
    main()
