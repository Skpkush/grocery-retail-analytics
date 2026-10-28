# Methodology and known limitations

## Data quality decisions

- **Orphan lines:** 4,836 transaction lines ($173 of sales across 17 product IDs)
  reference products missing from the product master. They are quarantined, not
  deleted, and the quality gate reconciles landing = fact + quarantine to the cent.
- **Fuel and gift cards** are excluded from merchandise metrics. Fuel quantities
  are not units, and gift card activations are liabilities, not revenue.
- **Promotions:** 12,785 product x store x week keys appear more than once in the
  source. They are merged to one row (promoted if any listing says so).
- **Demographics** exist for 801 of 2,469 households (32%). Demographic findings
  describe surveyed households only.
- **Time zone:** source timestamps are UTC. The first version of the pipeline used
  a fixed 05:00 cut-off, and the quality gate caught 785 rows assigned to the
  wrong week during daylight saving time. Converting to US Eastern time fixed it,
  and every row now matches the retailer's week number.

## Campaign impact (difference-in-differences)

- **Design:** treated = households targeted by a campaign; control = the 910
  households never targeted by any campaign. Outcome = weekly merchandise spend.
  The pre-period is the 8 weeks before launch and the post-period is the campaign
  window. OLS with campaign fixed effects and household-clustered standard errors.
- **Placebo test:** the same model on the 8 weeks before the pre-period. A
  significant placebo "effect" means treated and control households were already
  on different trends, so the parallel-trends assumption fails.
- **Result:** the placebo test fails for all three campaign types. Targeted
  households' spend was already declining relative to controls before launch,
  which means targeting selects declining shoppers. The campaign "lift" is
  therefore not identified.
- **Recommendation:** randomly hold out 10% of each target list.

## Coupon incrementality (proxy)

- **Definition:** a redemption is "habitual" when the household bought any product
  covered by that coupon in the 56 days before redeeming.
- **Scope:** only redemptions on or after 26 Feb 2017 are scored, so each one has a
  full look-back inside the data.
- **Interval:** 95% confidence intervals are Wilson score intervals.
- **Caveat:** this is a proxy. A habitual buyer might still have bought more
  because of the coupon.

## Promotion lift

- **Comparison:** each product x store pair's average weekly sales in promoted
  weeks, against the same pair's unpromoted weeks (weeks 2-52; a week with no
  sale counts as $0). Lift = sum of promoted averages / sum of baseline
  averages - 1.
- **Interval:** a bootstrap over pairs (300 resamples) gives the 95% interval.
- **Caveat:** promotions are not randomly assigned. Retailers promote seasonal or
  trending items, so the lift is an upper bound on the causal effect.

## Segments

- **RFM:** quintile scores on recency, frequency and monetary value; the snapshot
  date is 2018-01-01.
- **Deal dependence:** each household's share of merchandise spend bought with a
  loyalty discount.
