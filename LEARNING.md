# Learning dbt with this project

This guide explains how the dbt project in this repository works and why it is built the
way it is. Every example points at a real file, so you can open it while you read.

---

## 1. What dbt does

dbt (data build tool) turns `SELECT` statements into tables and views in a warehouse.
You write one `.sql` file per model, each holding a single `SELECT`. dbt then:

1. works out the order to build them in, from the references between them;
2. wraps each `SELECT` in the right `CREATE TABLE` / `CREATE VIEW` / `INSERT` statement;
3. runs the tests you declared, and stops if a serious one fails;
4. generates a documentation website with a lineage graph.

dbt does not move data in from outside. Here, `python -m retail.ingest` downloads the
files, and dbt-duckdb reads them where they sit.

The one command you will use most:

```bash
dbt build        # run every model, test and unit test in dependency order
```

`dbt run` builds models only, and `dbt test` runs tests only. `dbt build` interleaves them:
a model's tests run right after the model, and anything downstream of a failed test is
skipped.

---

## 2. Why staging, intermediate and marts?

Each layer has one job, so when something is wrong you know where to look.

| Layer | Job | Rule of thumb | Example |
|---|---|---|---|
| **Staging** (`stg_`) | Make each source table clean and typed | 1:1 with a source table. Rename, cast, trim. **No joins.** | [`stg_completejourney__transactions`](models/staging/stg_completejourney__transactions.sql) casts every column and converts UTC to store-local time |
| **Intermediate** (`int_`) | Business logic that several marts share | Joins and calculations; not used by end users | [`int_transactions__enriched`](models/intermediate/int_transactions__enriched.sql) adds product flags (fuel, gift card, orphan) to each line |
| **Marts** (`fct_`, `dim_`, `mart_`) | What dashboards and analysts read | Clear grain, stable names, fully tested | [`fct_sales`](models/marts/core/fct_sales.sql), [`dim_household`](models/marts/core/dim_household.sql), [`mart_rfm_segments`](models/marts/analytics/mart_rfm_segments.sql) |

Why bother splitting it up?

- **One place per rule.** The UTC-to-Eastern time conversion lives only in staging. If it
  were copied into three marts, a fix would have to be made three times.
- **Reuse.** `int_transactions__enriched` feeds `fct_sales`, `quarantine_transactions`,
  `dim_household` and `fct_baskets`. The product join is written once.
- **Readable lineage.** The graph in the README reads left to right: raw → clean → logic → output.

**Naming.** `stg_<source>__<table>` (double underscore between source and table), and
`int_<entity>__<verb>`. A `fct_` table holds events (one row per sale, per redemption), a
`dim_` table holds things that describe them (one row per product, per household).

---

## 3. `ref()` vs `source()`

Both replace a hard-coded table name.

```sql
-- a raw table that dbt does not build: declared in _sources.yml
select * from {{ source('completejourney', 'transactions') }}

-- a model that dbt builds
select * from {{ ref('stg_completejourney__transactions') }}
```

- **`source()`** points at raw data. Sources are declared once in
  [`models/staging/_sources.yml`](models/staging/_sources.yml). Here each source is a Parquet
  file, and the `external_location` setting tells dbt-duckdb where it is. The `ci` target
  points the same sources at the CSV sample instead, without touching any model.
- **`ref()`** points at another model. This is how dbt learns the dependency graph: if
  model B contains `ref('A')`, dbt builds A first. It also fills in the right schema for the
  environment you are running in.

Rule: only staging models use `source()`. Everything else uses `ref()`. If you write a raw
table name instead, dbt cannot see the dependency: the build order and the lineage graph
both break.

---

## 4. Materializations used here, and why

A materialization is *how* dbt stores a model. It is set in
[`dbt_project.yml`](dbt_project.yml) per folder, and can be overridden in a model's
`config()` block.

| Materialization | What dbt creates | Used for | Why |
|---|---|---|---|
| **view** | `CREATE VIEW` — nothing is stored; the query runs when read | All staging models | Staging is a thin layer over files that are already on disk. Storing a copy would just duplicate them. |
| **ephemeral** | Nothing in the warehouse. dbt pastes the SQL into each model that uses it, as a CTE | All intermediate models | They are building blocks, not outputs. Keeping them out of the warehouse means nobody builds a dashboard on them by accident. Downside: you cannot query one directly when debugging. |
| **table** | `CREATE TABLE AS SELECT` — rebuilt from scratch each run | Most marts | Dashboards read these many times; a stored table is fast. They are small enough to rebuild in seconds. |
| **incremental** | A table that, after the first run, only processes new or changed rows | `fct_sales`, `fct_promotions` | The two largest tables. On a real daily feed, reprocessing a whole year every night would be wasteful. |

---

## 5. How the incremental model works

Open [`models/marts/core/fct_sales.sql`](models/marts/core/fct_sales.sql).

```sql
{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='business_date'
) }}

select ...
from {{ ref('int_transactions__enriched') }}
where not is_orphan_product
{% if is_incremental() %}
  and business_date >= (select max(business_date) - interval 3 day from {{ this }})
{% endif %}
```

**First run** (or `dbt build --full-refresh`): `is_incremental()` is false, so the filter
is skipped and the whole table is built.

**Every later run:** `is_incremental()` is true, so only lines dated on or after the latest
loaded date minus 3 days are selected. dbt then:

1. writes those rows to a temporary table;
2. **deletes** every row in `fct_sales` whose `business_date` appears in the temporary table;
3. **inserts** the temporary rows.

**Why `delete+insert` on a date, not `merge` on a row key?** A merge needs a unique key per
row, and this data has none: two identical lines in the same basket are a real sale of two
items. So the table is reloaded one whole trading day at a time. Any day inside the window
is replaced completely, which can never create duplicates.

**Why a 3-day lookback?** On a real feed, some lines arrive late (a store uploads a day
behind). Reloading the last 3 days catches them. The window is a variable
(`incremental_lookback_days` in `dbt_project.yml`), so it can change without editing SQL.

**What `{{ this }}` means:** the model's own existing table in the warehouse.

`fct_promotions` uses the same pattern keyed on `week`. A second `dbt run` on the full data
deletes and reloads only the latest days and weeks, and leaves both tables at exactly
1,464,471 and 20,927,744 rows.

---

## 6. How each test type works

A dbt **data test** is a query that returns the rows that break a rule. **Zero rows = pass.**

### Generic tests (declared in YAML)

Written once, reused on any column. In [`_core__models.yml`](models/marts/core/_core__models.yml):

```yaml
- name: product_id
  data_tests:
    - unique                 # no value appears twice
    - not_null               # no nulls
    - relationships:         # every value exists in another model (a foreign key check)
        arguments:
          to: ref('dim_product')
          field: product_id
```

- `unique`, `not_null`, `accepted_values`, `relationships` come with dbt.
- `dbt_utils.unique_combination_of_columns` checks a composite key such as
  `(product_id, store_id, week)`.
- `dbt_utils.accepted_range` checks for example that no discount is negative.
- `dbt_utils.expression_is_true` checks a row-level rule such as `end_date >= start_date`.

### Singular tests (SQL files in `tests/dbt/`)

For a rule no generic test covers, write the query yourself.
[`assert_transaction_rows_reconcile.sql`](tests/dbt/assert_transaction_rows_reconcile.sql)
returns a row only if source lines ≠ `fct_sales` + `quarantine_transactions`.

### Severity and thresholds

By default a failing test is an **error**: `dbt build` fails and skips everything
downstream. Some problems are known and accepted, so they are tracked with a ceiling instead:

```sql
{{ config(severity='warn', warn_if='>10000') }}
select * from {{ ref('quarantine_transactions') }}
```

This warns only if more than 10,000 lines are quarantined (today there are 4,836), and
never blocks the build. `fail_calc` changes what is counted: the duplicate-promotion test
sums `source_rows - 1` instead of counting rows.

### Unit tests

Data tests check the real data. **Unit tests** check the *logic* on a few rows you make up,
like a unit test in software. In [`_staging__models.yml`](models/staging/_staging__models.yml),
`test_business_date_uses_store_local_time` feeds four UTC timestamps into the transactions
staging model and checks the trading dates that come out, including the daylight-saving
change and the New Year boundary. Unit tests run before the model is built, so wrong logic
is caught before it touches real data.

### How this project uses them

The original Python pipeline had 24 hand-written quality checks. Each one is now one or more
dbt tests tagged with `meta: {dq_check: "<check name>"}`. After `dbt build`,
[`src/retail/quality.py`](src/retail/quality.py) reads dbt's `target/run_results.json` and
`target/manifest.json`, groups the tests by check name and writes the report that the
Streamlit app shows.

---

## 7. What exposures are

An exposure declares something *outside* dbt that depends on your models: a dashboard, an
app, an ML model. See [`models/exposures.yml`](models/exposures.yml):

```yaml
exposures:
  - name: power_bi_retail_report
    type: dashboard
    depends_on:
      - ref('fct_sales')
      - ref('mart_rfm_segments')
      ...
```

Exposures build nothing. They:

- appear at the end of the lineage graph (the orange nodes), so anyone changing
  `mart_rfm_segments` can see that the Power BI report reads it;
- let you build only what a dashboard needs: `dbt build --select +exposure:power_bi_retail_report`;
- record an owner, so it is clear who to tell when a model changes.

---

## 8. Other pieces worth knowing

- **`dbt_project.yml`** — project settings: folder paths, default materializations per
  folder, and `vars` (dates, the 56-day look-back, the incremental window) used as
  `{{ var('habitual_lookback_days') }}` in SQL.
- **`profiles.yml`** — how to connect. With DuckDB that is just a file path, so there are no
  secrets. Two targets: `dev` (full data) and `ci` (the sample). `--target ci` switches.
- **`packages.yml`** — dbt packages, installed by `dbt deps` into `dbt_packages/`, like `pip`.
- **`analyses/`** — SQL that dbt compiles (so `ref()` works and lineage is tracked) but never
  runs. Here they are the 13 business-question queries the app and reports use.
- **`target/`** — dbt's output: compiled SQL, `manifest.json` (everything about the project)
  and `run_results.json` (what happened in the last run). Not committed.
- **Jinja** — the `{{ }}` and `{% %}` syntax. `{{ }}` prints a value; `{% if %}` adds logic.

---

## 9. Interview questions about this project

**1. Walk me through the project in two minutes.**
A grocery retailer wants to know who drives sales and whether its promotions work. I took
1.46M real transactions, built a dbt project on DuckDB with staging, intermediate and mart
layers and 102 data tests, and fed the marts to a Power BI report and a Streamlit app. The
headline findings: 21% of households bring in 45.7% of sales, about half of coupon
redemptions go to people already buying the product, and the campaign data cannot show any
effect because targeted households were already trending down, so I recommended a random
holdout.

**2. Why dbt instead of the Python scripts you had before?**
The old pipeline ran SQL files in filename order and kept quality checks in a separate
Python list. dbt gives me the build order from `ref()`, tests next to the models they check,
a lineage graph, docs, and incremental models, without writing that machinery myself.

**3. Why is staging a view and the marts tables?**
Staging is a light, typed layer over files already on disk, so a view costs nothing to store.
Marts are read many times by dashboards, so they are stored tables. Intermediate models are
ephemeral because they are building blocks, not outputs.

**4. How does your incremental model avoid duplicates without a primary key?**
There is no line-level key, because identical lines are real sales. So I use `delete+insert`
on `business_date`: each run deletes whole trading days from the lookback window onward and
inserts them again. A day is always replaced in full, so nothing is counted twice.

**5. What happens if late data arrives a week late?**
It falls outside the 3-day window, so it is missed until someone widens
`incremental_lookback_days` or runs `--full-refresh`. In production I would size the window
from how late data actually arrives, and schedule a weekly full refresh as a safety net.

**6. How did you know the dbt version produced the same numbers as the old pipeline?**
Before deleting the old SQL, I compared every table row by row against the old warehouse on
the full data with `EXCEPT ALL` in both directions. All rows matched. The only differences
were flags that changed from NULL to false for 528 products with no type, and float rounding
below $1e-13 in 13 basket totals. The DiD results were identical.

**7. Give an example of a test that caught a real problem.**
The derived-week test. My first time rule used a fixed cut-off hour, and the check found 785
lines landing in the wrong retail week around the daylight-saving change. Converting from
UTC to US Eastern time properly fixed it, and the test now passes on all 1.46M lines.

**8. How do you handle bad source rows?**
I never delete them silently. 4,836 lines reference products that do not exist; they go to
`quarantine_transactions`, and a test proves source rows = fact + quarantine, and that the
sales total matches to the cent. A warn-level test watches the quarantine size.

**9. What is the difference between a data test and a unit test?**
A data test checks the real data after a model is built, for example that `product_id` is
unique. A unit test checks the logic on rows I made up, before the model is built, for
example that a 04:01 UTC sale on 1 Jan 2018 lands on 31 Dec 2017.

**10. Why are some tests warnings instead of errors?**
Some issues are known properties of the source, like the 801-of-2,469 survey coverage. Failing
the build on them would block every run for no reason, but ignoring them hides changes. A
warning with a ceiling (`warn_if='>2000'`) keeps them visible and alerts if they grow.

**11. How does CI work if the data is too big to commit?**
I committed a sample of 9 whole households (5,899 lines), picked across six groups so it
includes targeted and never-targeted households, survey answers and coupon redemptions. A
`ci` target in `profiles.yml` points the sources at that sample, and GitHub Actions runs
`dbt build --target ci` on every push.

**12. Why sample whole households instead of random rows?**
Random rows would break baskets, RFM scores and redemption look-backs, because those depend
on a household's full history. Whole households keep every relationship intact, so the same
tests pass.

**13. Explain the difference-in-differences finding.**
I compared weekly spend of targeted households with households never targeted, before and
after each launch. The test only works if both groups were on the same trend beforehand. A
placebo test on two pre-launch windows showed they were not: targeted households were already
spending up to $5.26 less per week. So the campaign effect cannot be separated from that
trend, and I recommended a random holdout instead of reporting a misleading lift.

**14. Why is part of the DiD in dbt and part in Python?**
dbt builds the panel (`fct_campaign_spend_panel`) and the simple 2×2 means
(`mart_campaign_did`), which are plain aggregations. Confidence intervals with
household-clustered standard errors need a regression, so `stats.py` fits that with
statsmodels on the dbt panel. The SQL 2×2 estimates and the regression estimates match.

**15. What would you change to run this in production?**
Move from a local DuckDB file to a cloud warehouse (dbt-snowflake or dbt-bigquery, same
models), schedule `dbt build` daily, add source freshness on `transaction_timestamp`, store
test failures (`store_failures`) for investigation, and publish the docs site. I would also
add a random holdout to campaigns so their effect can finally be measured.
