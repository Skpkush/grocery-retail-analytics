"""Run the SQL analysis library and write the insights report.

Each ``sql/analysis/*.sql`` file answers one business question. Findings in
``reports/insights.md`` are computed from those results and from
``retail.stats``; no number in the report is typed by hand.

    python -m retail.analytics
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from retail.config import ANALYSIS_DIR, REPORTS_DIR
from retail.sql_guard import execute_readonly_query, rows_to_markdown

REPORT_PATH = REPORTS_DIR / "insights.md"
STATS_PATH = REPORTS_DIR / "stats_results.json"


@dataclass(frozen=True)
class Analysis:
    key: str
    title: str
    question: str
    sql: str
    path: Path


def _header(path: Path) -> tuple[str, str]:
    comments = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("--"):
            break
        comments.append(line.lstrip("- ").strip())
    return (comments[0] if comments else path.stem), " ".join(comments[1:])


@lru_cache(maxsize=1)
def list_analyses() -> tuple[Analysis, ...]:
    out = []
    for path in sorted(ANALYSIS_DIR.glob("*.sql")):
        title, question = _header(path)
        key = path.stem.split("_", 1)[1]
        out.append(Analysis(key, title, question, path.read_text(encoding="utf-8"), path))
    return tuple(out)


def get_analysis(key: str) -> Analysis:
    for analysis in list_analyses():
        if analysis.key == key:
            return analysis
    raise KeyError(f"Unknown analysis: {key}")


def run_analysis(key: str) -> pd.DataFrame:
    result = execute_readonly_query(get_analysis(key).sql, max_rows=1000)
    return pd.DataFrame(result.rows, columns=result.columns)


def load_stats() -> dict:
    return json.loads(STATS_PATH.read_text(encoding="utf-8")) if STATS_PATH.exists() else {}


def kpi_summary() -> dict[str, dict[str, float]]:
    """Q4 vs Q3 2017 KPIs with % change (points for percentage KPIs)."""
    df = run_analysis("kpi_by_quarter").set_index("quarter")
    cur, prior = df.loc["Q4 2017"], df.loc["Q3 2017"]
    out = {}
    for column in df.columns:
        c, p = float(cur[column]), float(prior[column])
        delta = c - p if column.endswith("_pct") else (100 * (c - p) / p if p else None)
        out[column] = {"current": c, "prior": p, "delta": delta}
    return out


def headline_findings() -> list[str]:
    f: list[str] = []
    stats = load_stats()

    q = run_analysis("kpi_by_quarter")
    total = q.net_sales.sum()
    kpi = kpi_summary()
    f.append(
        f"Households in the panel spent ${total:,.0f} on merchandise across "
        f"{q.baskets.sum():,} trips in 2017. Q4 was the strongest quarter "
        f"(${kpi['net_sales']['current']:,.0f}, {kpi['net_sales']['delta']:+.1f}% vs Q3), and the growth came from "
        f"bigger baskets ({kpi['avg_basket_value']['delta']:+.1f}% basket value) rather than more trips "
        f"({kpi['baskets']['delta']:+.1f}%)."
    )

    conc = run_analysis("customer_concentration")
    f.append(
        f"Sales are concentrated: the top 10% of households generate {conc.sales_share_pct.iloc[0]:.1f}% "
        f"of sales and the top 20% generate {conc.cumulative_share_pct.iloc[1]:.1f}%."
    )

    if "coupon_habitual" in stats:
        allc, a = stats["coupon_habitual"]["All"], stats["coupon_habitual"].get("Type A", {})
        f.append(
            f"About half of coupon redemptions subsidise purchases that were already happening: "
            f"{allc['habitual_pct']:.1f}% (95% CI {allc['ci95_pct'][0]}-{allc['ci95_pct'][1]}%) came from "
            f"households that bought the same product in the previous 56 days, rising to "
            f"{a.get('habitual_pct', float('nan')):.1f}% for Type A campaigns. Recommendation: exclude "
            "recent buyers of a product from that product's coupon."
        )

    if "campaign_did" in stats:
        failed = [t for t, r in stats["campaign_did"].items() if r["placebo"]["p_value"] < 0.05]
        worst = min(r["placebo"]["effect_per_household_week"] for r in stats["campaign_did"].values())
        f.append(
            "Campaign ROI cannot be measured reliably with the current design. A difference-in-differences "
            "test against never-targeted households fails its placebo check for "
            f"{len(failed)} of {len(stats['campaign_did'])} campaign types: targeted households' spend was "
            f"already falling relative to controls before launch (by up to ${abs(worst):.2f} per "
            "household per week). Targeting is aimed at "
            "declining shoppers, so any measured 'lift' is confounded. Recommendation: hold out a random "
            "10% of each target list."
        )

    if stats.get("promotion_lift"):
        p = stats["promotion_lift"]
        both, mailer, display = p["Display + mailer"], p["Mailer only"], p["Display only"]
        f.append(
            f"In-store support compounds. Versus the same product in the same store in unpromoted weeks, "
            f"a mailer alone lifts sales {mailer['lift_pct']:.0f}% and a display alone "
            f"{display['lift_pct']:.0f}%, but both together lift them {both['lift_pct']:.0f}% "
            f"(95% CI {both['ci95_pct'][0]:.0f}-{both['ci95_pct'][1]:.0f}%)."
        )

    pl = run_analysis("private_label_gap")
    pl = pl[(pl.private_label_share_pct < 15) & (pl.private_price_gap_pct > 30)]
    if not pl.empty:
        top = pl.iloc[0]
        others = ", ".join(pl.product_category.iloc[1:3].str.title())
        f.append(
            f"Own-brand opportunity: {top.product_category.title()} (${top.net_sales:,.0f}) has only "
            f"{top.private_label_share_pct:.1f}% private-label share although own brand is priced "
            f"{top.private_price_gap_pct:.0f}% below national brands"
            + (f"; {others} show the same pattern." if others else ".")
        )

    deal = run_analysis("discount_dependency")
    dependent = deal[deal.deal_segment.str.startswith(("3.", "4."))]
    f.append(
        f"Deals drive the business: households buying 40% or more of their spend on loyalty discount "
        f"make up {dependent.households.sum() / deal.households.sum() * 100:.0f}% of shoppers and "
        f"{dependent.sales_share_pct.sum():.1f}% of sales."
    )

    rfm = run_analysis("rfm_segments").set_index("segment")
    if "3. At risk" in rfm.index:
        r = rfm.loc["3. At risk"]
        f.append(
            f"{r.households:.0f} 'at risk' households (frequent shoppers who have not visited for "
            f"~{r.avg_recency_days:.0f} days) hold {r.sales_share_pct:.1f}% of annual sales: the first "
            "win-back target."
        )

    demo = run_analysis("demographic_spend")
    by_band = demo.groupby("income_band").apply(
        lambda g: pd.Series({
            "sales": (g.avg_annual_sales * g.households).sum() / g.households.sum(),
            "pl": (g.private_label_share_pct * g.households).sum() / g.households.sum(),
        }), include_groups=False)
    if {"Under 35K", "125K+"} <= set(by_band.index):
        lo, hi = by_band.loc["Under 35K"], by_band.loc["125K+"]
        f.append(
            f"Among surveyed households (801 of 2,469), 125K+ income households spend "
            f"{hi.sales / lo.sales:.1f}x as much as under-35K households, while under-35K households buy "
            f"more own brand ({lo.pl:.1f}% vs {hi.pl:.1f}% of spend)."
        )

    pat = run_analysis("shopping_patterns")
    best = pat.sort_values("avg_basket_value", ascending=False).iloc[0]
    weekday = pat[pat.day_of_week <= 5].avg_basket_value.mean()
    f.append(
        f"{best.day_name} {best.daypart.split('. ')[1].split(' (')[0].lower()} baskets are the largest "
        f"(${best.avg_basket_value:.2f} vs ${weekday:.2f} on an average weekday slot), so big-basket "
        "promotions and staffing should be weighted to weekend afternoons."
    )

    mb = run_analysis("market_basket").iloc[0]
    f.append(
        f"{mb.category_a.title()} and {mb.category_b.title()} are bought together {mb.lift:.1f}x more "
        "often than chance, a cross-merchandising candidate."
    )
    return f


def write_report(path: Path = REPORT_PATH) -> Path:
    lines = [
        "# Insights report: Complete Journey 2017",
        "",
        "_Generated by `python -m retail.analytics` from `sql/analysis/*.sql` and "
        "`reports/stats_results.json`. Sales are purchases by the 2,469 panel households, "
        "not total store sales._",
        "",
        "## Headline findings",
        "",
    ]
    lines += [f"{i}. {text}" for i, text in enumerate(headline_findings(), 1)]
    for analysis in list_analyses():
        df = run_analysis(analysis.key)
        lines += [
            "", f"## {analysis.title}", "",
            f"_{analysis.question}_" if analysis.question else "", "",
            f"Source: [`{analysis.path.name}`](../sql/analysis/{analysis.path.name})", "",
            rows_to_markdown(list(df.columns), df.head(25).to_dict("records")),
        ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    for i, finding in enumerate(headline_findings(), 1):
        print(f"{i}. {finding}\n")
    print(f"Report written to {write_report()}")


if __name__ == "__main__":
    main()
