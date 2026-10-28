"""Run the real SQL models on a tiny fixture: business rules without real data."""

from __future__ import annotations

import duckdb
import pytest

from retail.config import MODELS_DIR
from retail.quality import CHECKS

FIXTURE = """
CREATE VIEW landing_products AS SELECT * FROM (VALUES
  ('P1', 'M1', 'GROCERY', 'National', 'SOFT DRINKS', 'SOFT DRINKS 12/18', '12 OZ'),
  ('P2', 'M2', 'GROCERY', 'Private', 'SOFT DRINKS', 'SOFT DRINKS 12/18', '12 OZ'),
  ('FUEL1', 'M3', 'FUEL', 'National', 'COUPON/MISC ITEMS', 'GASOLINE-REG UNLEADED', NULL),
  ('GC1', 'M4', 'MISCELLANEOUS', 'National', 'COUPON/MISC ITEMS', 'ELECTRONIC GIFT CARDS ACTIVATI', NULL)
) t(product_id, manufacturer_id, department, brand, product_category, product_type, package_size);

CREATE VIEW landing_transactions AS SELECT * FROM (VALUES
  -- winter: 04:59 UTC Mon 2 Jan is still Sunday 1 Jan in the store (week 1)
  ('H1', 'S1', 'B1', 'P1', 2.0, 3.00, 0.50, 0.0, 0.0, 1, TIMESTAMP '2017-01-02 04:59:58'),
  -- winter: 05:05 UTC Mon 2 Jan is Monday 2 Jan local (week 2)
  ('H1', 'S1', 'B2', 'P2', 1.0, 1.20, 0.00, 0.0, 0.0, 2, TIMESTAMP '2017-01-02 05:05:54'),
  -- summer (EDT): 04:30 UTC Mon 3 Jul is Monday 00:30 local (week 28)
  ('H2', 'S1', 'B3', 'P1', 1.0, 2.00, 0.25, 0.10, 0.05, 28, TIMESTAMP '2017-07-03 04:30:00'),
  -- New Year: 04:01 UTC 1 Jan 2018 is 23:01 on 31 Dec 2017 local (week 53)
  ('H2', 'S1', 'B4', 'FUEL1', 9000.0, 30.00, 0.0, 0.0, 0.0, 53, TIMESTAMP '2018-01-01 04:01:20'),
  ('H2', 'S1', 'B4', 'GC1', 1.0, 25.00, 0.0, 0.0, 0.0, 53, TIMESTAMP '2018-01-01 04:01:20'),
  -- orphan: product not in master
  ('H1', 'S1', 'B5', 'NOPE', 1.0, 0.00, 0.0, 0.0, 0.0, 10, TIMESTAMP '2017-03-01 15:00:00')
) t(household_id, store_id, basket_id, product_id, quantity, sales_value, retail_disc,
    coupon_disc, coupon_match_disc, week, transaction_timestamp);

CREATE VIEW landing_demographics AS SELECT * FROM (VALUES
  ('H1', '35-44', '50-74K', 'Homeowner', 'Married', '2', '2 Adults No Kids', '0')
) t(household_id, age, income, home_ownership, marital_status, household_size, household_comp, kids_count);

CREATE VIEW landing_campaign_descriptions AS SELECT * FROM (VALUES
  ('C1', 'Type A', DATE '2017-06-01', DATE '2017-07-15')
) t(campaign_id, campaign_type, start_date, end_date);

CREATE VIEW landing_campaigns AS SELECT * FROM (VALUES ('C1', 'H2')) t(campaign_id, household_id);

CREATE VIEW landing_coupons AS SELECT * FROM (VALUES
  ('U1', 'P1', 'C1'), ('U1', 'P1', 'C1')   -- duplicate row, as in the source
) t(coupon_upc, product_id, campaign_id);

CREATE VIEW landing_coupon_redemptions AS SELECT * FROM (VALUES
  ('H2', 'U1', 'C1', DATE '2017-07-03')
) t(household_id, coupon_upc, campaign_id, redemption_date);

CREATE VIEW landing_promotions AS SELECT * FROM (VALUES
  ('P1', 'S1', '0', 'A', 28),
  ('P1', 'S1', '3', '0', 28)   -- same key listed twice with different placements
) t(product_id, store_id, display_location, mailer_location, week);
"""


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    c.execute(FIXTURE)
    for model in sorted(MODELS_DIR.glob("*.sql")):
        c.execute(model.read_text(encoding="utf-8"))
    yield c
    c.close()


def one(con, sql):
    return con.execute(sql).fetchone()


def test_business_date_uses_store_local_time(con):
    rows = dict(con.execute("SELECT basket_id, business_date::VARCHAR FROM stg_transactions").fetchall())
    assert rows["B1"] == "2017-01-01"  # 04:59 UTC Monday -> still Sunday in the store
    assert rows["B2"] == "2017-01-02"
    assert rows["B3"] == "2017-07-03"  # daylight saving: 04:30 UTC is 00:30 local
    assert rows["B4"] == "2017-12-31"  # the 2018 timestamp belongs to 2017


def test_derived_week_matches_source_week(con):
    mismatches = one(con, "SELECT COUNT(*) FROM stg_transactions s JOIN dim_date d "
                          "ON d.date_key = s.business_date WHERE d.retail_week <> s.source_week")[0]
    assert mismatches == 0


def test_orphans_are_quarantined_not_lost(con):
    assert one(con, "SELECT COUNT(*) FROM quarantine_transactions")[0] == 1
    assert one(con, "SELECT COUNT(*) FROM fct_sales")[0] == 5


def test_fuel_has_no_units_and_is_not_merchandise(con):
    units, is_merch = one(con, "SELECT units, is_merch FROM fct_sales WHERE product_id = 'FUEL1'")
    assert units is None and is_merch is False


def test_gift_cards_are_not_merchandise(con):
    assert one(con, "SELECT is_merch FROM fct_sales WHERE product_id = 'GC1'")[0] is False


def test_gross_sales_adds_back_retailer_discounts(con):
    gross = one(con, "SELECT gross_sales FROM fct_sales WHERE basket_id = 'B3'")[0]
    assert float(gross) == pytest.approx(2.00 + 0.25 + 0.05)  # coupon_disc is manufacturer funded


def test_baskets_hold_merchandise_only(con):
    assert one(con, "SELECT COUNT(*) FROM fct_baskets WHERE basket_id = 'B4'")[0] == 0


def test_duplicate_coupons_and_promotions_are_merged(con):
    assert one(con, "SELECT COUNT(*) FROM dim_coupon")[0] == 1
    display, mailer, n = one(con, "SELECT on_display, in_mailer, source_rows FROM fct_promotions")
    assert display and mailer and n == 2


def test_every_household_in_dimension_and_demographics_flagged(con):
    rows = dict(con.execute("SELECT household_id, has_demographics FROM dim_household").fetchall())
    assert rows == {"H1": True, "H2": False}


def test_blocking_quality_checks_pass_on_fixture(con):
    failures = [c.name for c in CHECKS if c.severity == "error"
                and int(con.execute(c.sql).fetchone()[0] or 0) > c.max_allowed]
    assert failures == []
