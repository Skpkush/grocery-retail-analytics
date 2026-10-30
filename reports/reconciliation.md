# Power BI to SQL reconciliation

**58 of 58 values match** (relative tolerance 1e-06).

DAX values come from the live Power BI model (`reports/powerbi_dax_results.json`). SQL values are recomputed independently against the DuckDB warehouse by `python -m retail.reconcile`. `tests/test_reconciliation.py` repeats the check on every test run.

| Check | DAX (Power BI) | SQL (DuckDB) | Match |
| --- | ---: | ---: | :---: |
| total/Net Sales | 4,198,540 | 4,198,540 | yes |
| total/Baskets | 141,180 | 141,180 | yes |
| total/Households | 2,467 | 2,467 | yes |
| total/Avg Basket Value | 29.738913 | 29.738913 | yes |
| total/Discount Rate % | 0.157324 | 0.157324 | yes |
| total/Private Label Share % | 0.215585 | 0.215585 | yes |
| total/Promo Sales Share % | 0.468330 | 0.468330 | yes |
| total/Top 10% Household Share | 0.341765 | 0.341765 | yes |
| total/Repeat Household Rate % | 0.987434 | 0.987434 | yes |
| total/Baskets per Household | 57.227402 | 57.227402 | yes |
| total/Scored Redemptions | 2,046 | 2,046 | yes |
| total/Habitual Redemptions | 1,036 | 1,036 | yes |
| total/Habitual Redemption % | 0.506354 | 0.506354 | yes |
| q4/Net Sales | 1,100,662 | 1,100,662 | yes |
| q4/Net Sales QoQ % | 0.062136 | 0.062136 | yes |
| q4/Avg Basket QoQ % | 0.074038 | 0.074038 | yes |
| rfm_segment/1. Champions/Households | 513 | 513 | yes |
| rfm_segment/1. Champions/Segment Sales Share % | 0.456867 | 0.456867 | yes |
| rfm_segment/2. Loyal/Households | 648 | 648 | yes |
| rfm_segment/2. Loyal/Segment Sales Share % | 0.287168 | 0.287168 | yes |
| rfm_segment/3. At risk/Households | 318 | 318 | yes |
| rfm_segment/3. At risk/Segment Sales Share % | 0.134206 | 0.134206 | yes |
| rfm_segment/4. New / occasional/Households | 165 | 165 | yes |
| rfm_segment/4. New / occasional/Segment Sales Share % | 0.027901 | 0.027901 | yes |
| rfm_segment/5. Lapsed/Households | 670 | 670 | yes |
| rfm_segment/5. Lapsed/Segment Sales Share % | 0.071875 | 0.071875 | yes |
| rfm_segment/6. Needs attention/Households | 153 | 153 | yes |
| rfm_segment/6. Needs attention/Segment Sales Share % | 0.021982 | 0.021982 | yes |
| deal_segment/1. Full-price (<25% on deal)/Households | 106 | 106 | yes |
| deal_segment/1. Full-price (<25% on deal)/Segment Sales Share % | 0.017738 | 0.017738 | yes |
| deal_segment/2. Balanced (25-40%)/Households | 562 | 562 | yes |
| deal_segment/2. Balanced (25-40%)/Segment Sales Share % | 0.244889 | 0.244889 | yes |
| deal_segment/3. Deal-leaning (40-55%)/Households | 1,200 | 1,200 | yes |
| deal_segment/3. Deal-leaning (40-55%)/Segment Sales Share % | 0.516551 | 0.516551 | yes |
| deal_segment/4. Deal-dependent (55%+)/Households | 599 | 599 | yes |
| deal_segment/4. Deal-dependent (55%+)/Segment Sales Share % | 0.220822 | 0.220822 | yes |
| habitual_by_type/Type A | 0.545401 | 0.545401 | yes |
| habitual_by_type/Type B | 0.336667 | 0.336667 | yes |
| habitual_by_type/Type C | 0.262295 | 0.262295 | yes |
| department/GROCERY/Net Sales | 2,316,394 | 2,316,394 | yes |
| department/GROCERY/Product Penetration % | 0.995545 | 0.995545 | yes |
| department/GROCERY/Private Label Share % | 0.270921 | 0.270921 | yes |
| department/GROCERY/Discount Rate % | 0.164933 | 0.164933 | yes |
| department/DRUG GM/Net Sales | 596,827 | 596,827 | yes |
| department/DRUG GM/Product Penetration % | 0.973674 | 0.973674 | yes |
| department/DRUG GM/Private Label Share % | 0.096708 | 0.096708 | yes |
| department/DRUG GM/Discount Rate % | 0.090093 | 0.090093 | yes |
| department/PRODUCE/Net Sales | 322,859 | 322,859 | yes |
| department/PRODUCE/Product Penetration % | 0.951802 | 0.951802 | yes |
| department/PRODUCE/Private Label Share % | 0.133698 | 0.133698 | yes |
| department/PRODUCE/Discount Rate % | 0.115262 | 0.115262 | yes |
| department/MEAT/Net Sales | 308,575 | 308,575 | yes |
| department/MEAT/Product Penetration % | 0.880923 | 0.880923 | yes |
| department/MEAT/Private Label Share % | 0.048706 | 0.048706 | yes |
| department/MEAT/Discount Rate % | 0.250014 | 0.250014 | yes |
| promotion_lift/Display + mailer | 2.248000 | 2.248000 | yes |
| promotion_lift/Display only | 1.292000 | 1.292000 | yes |
| promotion_lift/Mailer only | 1.311000 | 1.311000 | yes |
