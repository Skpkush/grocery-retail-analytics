"""Semantic metric layer: one governed definition per business metric.

Every consumer (SQL library, Streamlit dashboard, copilot, Power BI DAX) uses
these definitions, and tests assert they agree. Expressions assume the aliases
``s`` (fct_sales) and ``p`` (dim_product).

Money terms in the Complete Journey data:
  sales_value        what the retailer receives for the line
  retail_disc        loyalty-card discount (retailer funded)
  coupon_match_disc  retailer's match of a manufacturer coupon (retailer funded)
  coupon_disc        manufacturer coupon (manufacturer funded)
  gross_sales        sales_value + retail_disc + coupon_match_disc (shelf price)
"""

from __future__ import annotations

from dataclasses import dataclass

# Merchandise excludes fuel and gift cards / non-merchandise lines.
MERCH_FILTER = "s.is_merch"


@dataclass(frozen=True)
class Metric:
    name: str
    sql: str
    description: str
    unit: str  # currency | percent | count | ratio
    needs_product: bool = False


METRICS: dict[str, Metric] = {
    m.name: m
    for m in (
        Metric("net_sales", "ROUND(SUM(s.sales_value), 2)",
               "Merchandise sales the retailer received.", "currency"),
        Metric("gross_sales", "ROUND(SUM(s.gross_sales), 2)",
               "Shelf-price sales before retailer-funded discounts.", "currency"),
        Metric("retailer_discount", "ROUND(SUM(s.retail_disc + s.coupon_match_disc), 2)",
               "Loyalty discounts plus coupon matches, funded by the retailer.", "currency"),
        Metric("manufacturer_coupons", "ROUND(SUM(s.coupon_disc), 2)",
               "Manufacturer-funded coupon value.", "currency"),
        Metric("discount_rate_pct",
               "ROUND(100.0 * SUM(s.retail_disc + s.coupon_match_disc) / NULLIF(SUM(s.gross_sales), 0), 1)",
               "Retailer-funded discount as a percent of gross sales.", "percent"),
        Metric("baskets", "COUNT(DISTINCT s.basket_id)", "Shopping trips.", "count"),
        Metric("households", "COUNT(DISTINCT s.household_id)", "Households that shopped.", "count"),
        Metric("units", "SUM(s.units)", "Units sold (fuel excluded).", "count"),
        Metric("avg_basket_value",
               "ROUND(SUM(s.sales_value) / NULLIF(COUNT(DISTINCT s.basket_id), 0), 2)",
               "Net sales per basket.", "currency"),
        Metric("units_per_basket",
               "ROUND(SUM(s.units) / NULLIF(COUNT(DISTINCT s.basket_id), 0), 2)",
               "Units per basket.", "ratio"),
        Metric("sales_per_household",
               "ROUND(SUM(s.sales_value) / NULLIF(COUNT(DISTINCT s.household_id), 0), 2)",
               "Net sales per shopping household.", "currency"),
        Metric("private_label_share_pct",
               "ROUND(100.0 * SUM(CASE WHEN p.brand = 'Private' THEN s.sales_value END)"
               " / NULLIF(SUM(s.sales_value), 0), 1)",
               "Share of net sales from the retailer's own brand.", "percent", needs_product=True),
        Metric("promo_sales_share_pct",
               "ROUND(100.0 * SUM(CASE WHEN s.retail_disc > 0 THEN s.sales_value END)"
               " / NULLIF(SUM(s.sales_value), 0), 1)",
               "Share of net sales sold with a loyalty discount.", "percent"),
    )
}


def select_metrics(*names: str) -> str:
    return ",\n  ".join(f"{METRICS[n].sql} AS {n}" for n in names)


def metric_glossary() -> str:
    lines = [f"- {m.name} = {m.sql}  -- {m.description}" for m in METRICS.values()]
    lines.append(f"- Always filter merchandise with: {MERCH_FILTER}")
    return "\n".join(lines)
