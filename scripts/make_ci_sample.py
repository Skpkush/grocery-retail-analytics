"""Build the small CI sample in sample_data/ from the landed full dataset.

The sample is whole households, not random rows, so baskets, RFM segments,
coupon redemptions and the campaign panel stay internally consistent. It mixes
households that were and were not targeted by campaigns (treated and control
groups), with and without survey answers and coupon redemptions. Every other
table is cut to what those households touch. The selection is deterministic.

    python scripts/make_ci_sample.py        # needs data/landing/*.parquet
"""

from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "data" / "landing"
OUT = ROOT / "sample_data"

# (targeted by a campaign, redeemed a coupon, answered the survey) -> households to take
STRATA = {
    (False, False, False): 3,
    (False, False, True): 1,
    (True, False, False): 1,
    (True, False, True): 1,
    (True, True, False): 1,
    (True, True, True): 2,
}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    con = duckdb.connect()
    for name in ("transactions", "products", "demographics", "campaigns", "campaign_descriptions",
                 "coupons", "coupon_redemptions", "promotions"):
        con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{(LANDING / name).as_posix()}.parquet')")

    con.execute("""
        CREATE TABLE household_profile AS
        SELECT
            t.household_id,
            count(*) AS lines,
            t.household_id IN (SELECT household_id FROM campaigns)          AS targeted,
            t.household_id IN (SELECT household_id FROM coupon_redemptions) AS redeemed,
            t.household_id IN (SELECT household_id FROM demographics)       AS surveyed
        FROM transactions AS t
        GROUP BY t.household_id
    """)
    picked: list[str] = []
    for (targeted, redeemed, surveyed), n in STRATA.items():
        # Typical households: line count within 20% of the stratum median, in hash order.
        rows = con.execute("""
            WITH s AS (
                SELECT *, median(lines) OVER () AS med FROM household_profile
                WHERE targeted = ? AND redeemed = ? AND surveyed = ?
            )
            SELECT household_id FROM s
            WHERE lines BETWEEN 0.8 * med AND 1.2 * med
            ORDER BY hash(household_id), household_id
            LIMIT ?
        """, [targeted, redeemed, surveyed, n]).fetchall()
        picked += [r[0] for r in rows]
    con.execute("CREATE TABLE picked AS SELECT unnest(?) AS household_id", [picked])

    samples = {
        "transactions": "SELECT * FROM transactions WHERE household_id IN (SELECT household_id FROM picked)",
        "demographics": "SELECT * FROM demographics WHERE household_id IN (SELECT household_id FROM picked)",
        "campaigns": "SELECT * FROM campaigns WHERE household_id IN (SELECT household_id FROM picked)",
        "campaign_descriptions": "SELECT * FROM campaign_descriptions",
        "coupon_redemptions": "SELECT * FROM coupon_redemptions "
                              "WHERE household_id IN (SELECT household_id FROM picked)",
    }
    for name, sql in samples.items():
        con.execute(f"CREATE TABLE s_{name} AS {sql}")
    con.execute("""CREATE TABLE s_products AS SELECT * FROM products
                   WHERE product_id IN (SELECT product_id FROM s_transactions)""")
    con.execute("""CREATE TABLE s_coupons AS SELECT * FROM coupons
                   WHERE (coupon_upc, campaign_id) IN (SELECT (coupon_upc, campaign_id) FROM s_coupon_redemptions)""")
    con.execute("""CREATE TABLE s_promotions AS SELECT * FROM promotions
                   WHERE (product_id, store_id) IN (SELECT DISTINCT (product_id, store_id) FROM s_transactions)""")

    for name in ("transactions", "products", "demographics", "campaigns", "campaign_descriptions",
                 "coupons", "coupon_redemptions", "promotions"):
        path = (OUT / f"{name}.csv").as_posix()
        con.execute(f"COPY (SELECT * FROM s_{name} ORDER BY ALL) TO '{path}' (HEADER, DELIMITER ',')")
        rows = con.execute(f"SELECT count(*) FROM s_{name}").fetchone()[0]
        print(f"{name:22s} {rows:>7,} rows")
    print("households:", ", ".join(picked))


if __name__ == "__main__":
    main()
