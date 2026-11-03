"""Statistical tests behind the headline findings.

1. Campaign impact: difference-in-differences (DiD) on weekly household spend.
   Treated = households targeted by a campaign; control = households never
   targeted by any campaign. Pre = 8 weeks before launch; post = the campaign
   window. The panel is built in dbt (fct_campaign_spend_panel); this module
   fits OLS with campaign fixed effects and household-clustered standard errors.
   A placebo test on the 8 weeks before the pre-period checks the
   parallel-trends assumption.
2. Coupon habitual share: Wilson 95% interval on the proportion of redemptions
   by households that already bought the product.
3. Promotion lift: bootstrap 95% interval on the sales lift, resampling
   product x store pairs.

    python -m retail.stats
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from retail import sqlfiles
from retail.config import ANALYSIS_DIR, REPORTS_DIR
from retail.transform import connect

STATS_PATH = REPORTS_DIR / "stats_results.json"


def campaign_panel(con) -> pd.DataFrame:
    """Household x campaign x period panel, built in dbt (fct_campaign_spend_panel)."""
    return con.execute(
        "SELECT campaign_id, campaign_type, household_id, treated, period, weekly_spend "
        "FROM fct_campaign_spend_panel ORDER BY campaign_id, period, household_id").df()


def _did(panel: pd.DataFrame, before: str, after: str) -> dict:
    df = panel[panel.period.isin([before, after])].copy()
    df["post"] = (df.period == after).astype(int)
    model = smf.ols("weekly_spend ~ treated * post + C(campaign_id)", data=df).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(df.household_id)[0]})
    est = model.params["treated:post"]
    lo, hi = model.conf_int().loc["treated:post"]
    treated_pre = df[(df.treated == 1) & (df.post == 0)].weekly_spend.mean()
    return {
        "effect_per_household_week": round(float(est), 2),
        "ci95": [round(float(lo), 2), round(float(hi), 2)],
        "p_value": float(model.pvalues["treated:post"]),
        "treated_baseline_weekly_spend": round(float(treated_pre), 2),
        "effect_pct_of_baseline": round(100 * float(est) / treated_pre, 1) if treated_pre else None,
        "treated_households": int(df[df.treated == 1].household_id.nunique()),
        "control_households": int(df[df.treated == 0].household_id.nunique()),
        "campaigns": int(df.campaign_id.nunique()),
    }


def campaign_did(con) -> dict:
    panel = campaign_panel(con)
    results = {}
    for ctype, group in panel.groupby("campaign_type"):
        results[ctype] = {
            "did": _did(group, "pre", "post"),
            # Parallel-trends check: there should be no "effect" before launch.
            "placebo": _did(group, "placebo_pre", "pre"),
        }
    return results


def wilson(successes: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [math.nan, math.nan]
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return [round(100 * (centre - half), 1), round(100 * (centre + half), 1)]


def coupon_habitual(con) -> dict:
    df = con.execute(sqlfiles.read(ANALYSIS_DIR / "10_coupon_incrementality.sql")).df()
    out = {}
    for row in df.itertuples():
        key = row.campaign_type if isinstance(row.campaign_type, str) else "All"
        out[key] = {
            "redemptions": int(row.redemptions),
            "habitual_pct": float(row.habitual_pct),
            "ci95_pct": wilson(int(row.habitual_redemptions), int(row.redemptions)),
        }
    return out


def promotion_lift_ci(con, resamples: int = 300, seed: int = 7) -> dict:
    """Bootstrap the pair-level lift ratio (sum promoted / sum baseline)."""
    sql = sqlfiles.read(ANALYSIS_DIR / "11_promotion_lift.sql")
    # Reuse the analysis CTEs, stopping before the final aggregation.
    # Fixed row order: the bootstrap draws row positions, so an unordered result
    # would give a slightly different interval on every run.
    pairs_sql = sql.split("SELECT\n  promo_state,\n  COUNT(*)")[0] + (
        "SELECT promo_state, avg_sales, baseline_sales FROM paired "
        "ORDER BY promo_state, product_id, store_id")
    pairs = con.execute(pairs_sql).df()
    if pairs.empty:  # promotions skipped (RETAIL_SKIP_TABLES)
        return {}
    rng = np.random.default_rng(seed)
    out = {}
    for state, g in pairs.groupby("promo_state"):
        promoted, base = g.avg_sales.to_numpy(), g.baseline_sales.to_numpy()
        n = len(g)
        draws = np.empty(resamples)
        for i in range(resamples):
            idx = rng.integers(0, n, n)
            draws[i] = promoted[idx].sum() / base[idx].sum() - 1
        out[state] = {
            "lift_pct": round(100 * (promoted.sum() / base.sum() - 1), 1),
            "ci95_pct": [round(100 * float(np.percentile(draws, q)), 1) for q in (2.5, 97.5)],
            "pairs": n,
        }
    return out


def run() -> dict:
    con = connect(read_only=True)
    try:
        results = {
            "campaign_did": campaign_did(con),
            "coupon_habitual": coupon_habitual(con),
            "promotion_lift": promotion_lift_ci(con),
        }
    finally:
        con.close()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def main() -> None:
    print(json.dumps(run(), indent=2))


if __name__ == "__main__":
    main()
