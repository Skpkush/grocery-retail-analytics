"""Evidence-backed findings: claim, evidence, recommendation, caveat, confidence.

Every number is computed from the SQL library or reports/stats_results.json.
No financial savings or ROI are estimated: the data has no costs or margins,
and campaign effects are not identified (see finding 3).

Writes reports/findings.json (read by Power BI and the app) and reports/findings.md.

    python -m retail.findings
"""

from __future__ import annotations

import json

from retail.analytics import load_stats, run_analysis
from retail.config import REPORTS_DIR

JSON_PATH = REPORTS_DIR / "findings.json"
MD_PATH = REPORTS_DIR / "findings.md"

# How much weight a finding can bear, stated in plain terms.
CONFIDENCE = {
    "descriptive": "High: a direct measurement of what happened",
    "association": "Moderate: an association, not proven cause and effect",
    "proxy": "Moderate: a proxy measure, not a direct test",
    "not_identified": "Cannot conclude: the data cannot isolate the effect",
}


def build() -> list[dict]:
    stats = load_stats()
    findings: list[dict] = []

    # 1. Customer value concentration (descriptive)
    conc = run_analysis("customer_concentration")
    rfm = run_analysis("rfm_segments").set_index("segment")
    champ, risk = rfm.loc["1. Champions"], rfm.loc["3. At risk"]
    total_hh = int(rfm.households.sum())
    findings.append({
        "id": "customer_value",
        "title": "A small group of households drives most of the sales",
        "evidence": (
            f"The top 10% of households generate {conc.sales_share_pct.iloc[0]:.1f}% of merchandise sales. "
            f"RFM 'Champions' ({int(champ.households)} households, "
            f"{100 * champ.households / total_hh:.0f}% of shoppers) generate {champ.sales_share_pct:.1f}%. "
            f"{int(risk.households)} 'At risk' households (frequent shoppers, no visit for about "
            f"{risk.avg_recency_days:.0f} days) still hold {risk.sales_share_pct:.1f}% of annual sales."),
        "recommendation": "Make retention the priority: protect Champions and run win-back offers for "
                          "At-risk households before they lapse.",
        "caveat": "One year of data from a loyalty panel. RFM describes past behaviour and does not "
                  "predict who will leave. Segment boundaries are quintiles, not business thresholds.",
        "confidence": CONFIDENCE["descriptive"],
        "sources": ["sql/analysis/06_rfm_segments.sql", "sql/analysis/07_customer_concentration.sql"],
    })

    # 2. Coupons and existing buyers (proxy)
    c = stats.get("coupon_habitual", {})
    if c:
        allc, a = c["All"], c.get("Type A", {})
        findings.append({
            "id": "coupon_habitual",
            "title": "About half of coupon redemptions go to households already buying the product",
            "evidence": (
                f"{allc['habitual_pct']:.1f}% of {allc['redemptions']:,} scored redemptions "
                f"(95% CI {allc['ci95_pct'][0]}-{allc['ci95_pct'][1]}%) came from households that bought a "
                f"product covered by the coupon in the previous 56 days; {a.get('habitual_pct', 0):.1f}% "
                "for Type A campaigns."),
            "recommendation": "Leave a product's recent buyers out of its coupon mailings, and test the "
                              "change with a holdout before rolling it out.",
            "caveat": "A habitual buyer may still buy more because of the coupon, so this does not "
                      "measure lost incremental volume. It is a proxy for subsidised repeat purchases.",
            "confidence": CONFIDENCE["proxy"],
            "sources": ["sql/analysis/10_coupon_incrementality.sql", "reports/stats_results.json"],
        })

    # 3. Campaign effect not identifiable (not identified)
    d = stats.get("campaign_did", {})
    if d:
        failed = [t for t, r in d.items() if r["placebo"]["p_value"] < 0.05]
        worst = min(r["placebo"]["effect_per_household_week"] for r in d.values())
        reach = run_analysis("campaign_reach").set_index("campaign_type")
        findings.append({
            "id": "campaign_effect",
            "title": "The data cannot show whether campaigns increase spending",
            "evidence": (
                f"Difference-in-differences against the {d[next(iter(d))]['did']['control_households']} "
                f"never-targeted households fails its placebo test for {len(failed)} of {len(d)} campaign types. "
                f"Targeted households were already spending less than controls before launch, by up to "
                f"${abs(worst):.2f} per household per week. Redemption rates differ by type (Type A "
                f"{reach.loc['Type A', 'household_redemption_rate_pct']:.1f}%, Type B "
                f"{reach.loc['Type B', 'household_redemption_rate_pct']:.1f}%), but redemption is not "
                "the same as extra spend."),
            "recommendation": "Hold out a random 10% of every campaign's target list, so future campaigns "
                              "have a valid comparison group and ROI can be measured.",
            "caveat": "This does not say campaigns fail. It says the current targeting makes their "
                      "effect impossible to separate from the households' existing trend.",
            "confidence": CONFIDENCE["not_identified"],
            "sources": ["src/retail/stats.py", "reports/stats_results.json", "docs/methodology.md"],
        })

    # 4. Promotion support (association)
    p = stats.get("promotion_lift", {})
    if p:
        both, mailer, display = p["Display + mailer"], p["Mailer only"], p["Display only"]
        findings.append({
            "id": "promotion_lift",
            "title": "A display and a mailer together are linked to much higher sales than either alone",
            "evidence": (
                f"Against the same product in the same store in unpromoted weeks, weekly sales were "
                f"{mailer['lift_pct']:.0f}% higher with a mailer only, {display['lift_pct']:.0f}% higher "
                f"with a display only, and {both['lift_pct']:.0f}% higher with both "
                f"(95% CI {both['ci95_pct'][0]:.0f}-{both['ci95_pct'][1]:.0f}%, "
                f"{both['pairs']:,} product x store pairs)."),
            "recommendation": "When an item is featured in the mailer, give it an in-store display too, and "
                              "run a controlled store test to confirm the combined effect.",
            "caveat": "Promotions are not randomly assigned. Retailers promote items in season or already "
                      "trending, so these figures are an upper bound, not a causal lift. Sales are the "
                      "panel households' only.",
            "confidence": CONFIDENCE["association"],
            "sources": ["sql/analysis/11_promotion_lift.sql", "reports/stats_results.json"],
        })

    # 5. Basket affinity (descriptive)
    mb = run_analysis("market_basket").head(3)
    pairs = "; ".join(f"{r.category_a.title()} + {r.category_b.title()} (lift {r.lift:.1f})"
                      for r in mb.itertuples())
    findings.append({
        "id": "basket_affinity",
        "title": "Fresh-produce and meal-ingredient categories are bought together",
        "evidence": f"The strongest category pairs are {pairs}. Lift is how many times more often a pair "
                    "shares a basket than chance would predict.",
        "recommendation": "Place these categories near each other or bundle them in meal-solution "
                          "promotions, and track whether basket size rises.",
        "caveat": "This shows the categories are bought together, not that one causes the other. "
                  "Results are at category level, not for individual products.",
        "confidence": CONFIDENCE["descriptive"],
        "sources": ["sql/models/03_segments.sql", "sql/analysis/12_market_basket.sql"],
    })
    return findings


def write() -> list[dict]:
    findings = build()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    lines = ["# Findings and recommendations", "",
             "_Generated by `python -m retail.findings`. Each finding states its evidence, the "
             "recommended action, the caveat and how much weight it can bear. No financial savings or "
             "ROI are claimed: the data has no costs and campaign effects are not identified._", ""]
    for i, f in enumerate(findings, 1):
        lines += [f"## {i}. {f['title']}", "", f"**Evidence.** {f['evidence']}", "",
                  f"**Recommendation.** {f['recommendation']}", "", f"**Caveat.** {f['caveat']}", "",
                  f"**Confidence.** {f['confidence']}", "",
                  "**Sources.** " + ", ".join(f"`{s}`" for s in f["sources"]), ""]
    MD_PATH.write_text("\n".join(lines), encoding="utf-8")
    return findings


def main() -> None:
    for f in write():
        print(f"- {f['title']}\n  {f['evidence']}\n")
    print(f"Wrote {JSON_PATH} and {MD_PATH}")


if __name__ == "__main__":
    main()
