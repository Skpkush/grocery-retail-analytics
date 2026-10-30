# Power BI design guide: Grocery Retail Analytics

The complete design specification for `powerbi/Retail_Analytics.pbip`: design principles,
colours, fonts, layout grid, every page and visual (title, fields, position, formatting),
and step-by-step build instructions.

**Theme file:** [`powerbi/theme/grocery_retail_theme.json`](../powerbi/theme/grocery_retail_theme.json)
(validated against Microsoft's report-theme schema 2.159).

---

## Contents

1. [Design principles](#1-design-principles)
2. [Colour palette](#2-colour-palette)
3. [Typography](#3-typography)
4. [Canvas and layout grid](#4-canvas-and-layout-grid)
5. [Standard components](#5-standard-components)
6. [Page 1: Executive Overview](#page-1-executive-overview)
7. [Page 2: Customer Analytics](#page-2-customer-analytics)
8. [Page 3: Product Analytics](#page-3-product-analytics)
9. [Page 4: Promotion Effectiveness](#page-4-promotion-effectiveness)
10. [Page 5: Business Recommendations](#page-5-business-recommendations)
11. [Department Detail (drill-through)](#department-detail-drill-through)
12. [Step-by-step build guide](#12-step-by-step-build-guide)
13. [Final quality checklist](#13-final-quality-checklist)
14. [Screenshots for the README](#14-screenshots-for-the-readme)

---

## 1. Design principles

The audience is a **hiring manager or business leader with 30 seconds**. Every design
choice serves that.

| Principle | What it means in this report |
|---|---|
| **One question per page** | Each page title is the business question it answers. Nothing on the page is off-topic. |
| **Five-second rule** | Within five seconds a reader sees the headline numbers (KPI row) and the main pattern (largest chart). |
| **Z-pattern reading** | Title top-left, then KPIs left to right, then the main chart below-left and the detail table on the right. |
| **One accent colour** | Teal means "the measure". Amber means "comparison or caution". Nothing else gets a strong colour. |
| **Honest by design** | Associations are labelled as associations, and the campaign test shows its failed placebo. Captions state limits. |
| **Numbers you can defend** | Every visual uses a measure verified against SQL (`reports/reconciliation.md`). No new measures without re-reconciling. |
| **Less ink** | No 3D, no gradients, no gridlines on bar charts, no axis titles that repeat the visual title. |

---

## 2. Colour palette

### Core colours

| Role | Name | Hex | Where it is used |
|---|---|---|---|
| Primary | Deep Teal | `#0F766E` | Bars, lines, KPI values, table accent, links |
| Primary light | Teal 100 | `#CCFBF1` | Highlight backgrounds, selected slicer items |
| Accent | Amber | `#D97706` | Rolling averages, comparison series, placebo results, warnings |
| Ink | Slate 900 | `#0F172A` | Page titles, visual titles, table text |
| Secondary text | Slate 600 | `#475569` | Subtitles, axis labels, captions, card labels |
| Muted | Slate 400 | `#94A3B8` | Disabled items, "other" categories |
| Border | Slate 200 | `#E2E8F0` | Visual borders, table gridlines |
| Surface | White | `#FFFFFF` | Visual (card) backgrounds |
| Canvas | Slate 50 | `#F8FAFC` | Page background |
| Header band | Slate 100 | `#F1F5F9` | Table headers, optional header strip |

### Status colours (conditional formatting)

| Meaning | Hex | Rule |
|---|---|---|
| Good | `#15803D` | Sales, baskets and basket value **up** vs prior quarter |
| Bad | `#B91C1C` | Sales, baskets and basket value **down** vs prior quarter |
| Neutral | `#64748B` | No change, or not comparable |

> **Watch the inverted metric.** For **Discount Rate Change pts**, *down is good*. A
> lower discount rate means less margin given away, so reverse the colours for that card.

### Category colour sequence (theme `dataColors`)

Used only when a chart needs more than one series, in this order:

`#0F766E` teal · `#D97706` amber · `#2563EB` blue · `#7C3AED` violet · `#DB2777` pink · `#65A30D` green · `#0891B2` cyan · `#94A3B8` grey ("other")

### Accessibility

- Teal `#0F766E` on white has a contrast ratio of about **5.5:1** (passes WCAG AA for text).
- Slate 600 `#475569` on white is about **7.6:1** (passes AA, and AAA for large text).
- **Never use colour alone to carry meaning.** Delta cards show a `+` or `-` sign, and the
  campaign table has a `significant` TRUE/FALSE column.

---

## 3. Typography

Font: **Segoe UI** (Power BI default, always available). Use **Segoe UI Semibold** for emphasis.

| Element | Size | Weight | Colour |
|---|---|---|---|
| Page title | 20 pt | Bold | `#0F172A` |
| Page subtitle | 10 pt | Regular | `#475569` |
| Visual title | 12 pt | Semibold | `#0F172A` |
| KPI card value (main row) | 22 to 26 pt | Semibold | `#0F766E` |
| KPI card value (delta row) | 16 pt | Semibold | Good / bad colour |
| KPI card label | 10 pt | Regular | `#475569` |
| Table header | 10 pt | Semibold | `#0F172A` on `#F1F5F9` |
| Table values | 10 pt | Regular | `#0F172A` |
| Data labels | 9 pt | Regular | `#475569` |
| Caption or footnote | 9 pt | Regular | `#475569` |

Rules:

- **Titles say what the reader learns,** not what the chart is: "Share of sales by RFM segment", not "Bar chart".
- **Sentence case everywhere** ("Net sales by department"), never Title Case or ALL CAPS.
- **Units belong in the title or number format,** not the axis title.

---

## 4. Canvas and layout grid

| Setting | Value |
|---|---|
| Page size | 16:9, **1280 x 720 px** (Format page → Canvas settings) |
| Page background | `#F8FAFC`, 0% transparency |
| Outer margin | **20 px** on all sides |
| Gutter between visuals | **15 px** |
| Grid unit | 5 px (View → turn on Gridlines and Snap to grid) |
| Header zone | y = 5 to 75 (page title and subtitle) |
| KPI zone | y = 80 to 175 (cards, 95 px high) |
| Content zone | y = 190 to 700 |

```text
 20px                                                                 1260px
 ┌──────────────────────────────────────────────────────────────────────┐  y=5
 │ Page title (20pt bold)                                               │
 │ Subtitle: what the page covers, data scope (10pt slate)              │  y=75
 ├──────────┬──────────┬──────────┬──────────┬──────────┐               │  y=80
 │  KPI 1   │  KPI 2   │  KPI 3   │  KPI 4   │  KPI 5   │  (cards, 95px) │
 ├──────────┴──────────┴──────────┴──────────┴──────────┘               │  y=175
 │ ┌────────────────────────────┐ ┌───────────────────────────────────┐ │  y=190
 │ │ Main chart (largest)       │ │ Detail table                      │ │
 │ │                            │ │                                   │ │
 │ └────────────────────────────┘ └───────────────────────────────────┘ │
 │ ┌────────────────────────────┐ ┌───────────────────────────────────┐ │
 │ │ Supporting chart           │ │ Supporting chart / table          │ │
 │ └────────────────────────────┘ └───────────────────────────────────┘ │  y=700
 └──────────────────────────────────────────────────────────────────────┘
```

---

## 5. Standard components

The theme applies these automatically; the values are here so you can apply them by hand.

### Visual container (every chart, card and table)
- Background: white `#FFFFFF`, 0% transparency
- Border: on, `#E2E8F0`, **rounded corners 8 px**
- Shadow: off
- Padding: 10 px top/bottom, 12 px left/right
- Title: on, 12 pt Segoe UI Semibold, `#0F172A`, left-aligned

### KPI card
- Value: 22 to 26 pt Semibold, teal `#0F766E`
- Category label: on, 10 pt, `#475569`
- Use the **card's title** for the business label (for example "Net sales (Q4)") and keep the data label on.
- Delta cards: 16 pt with conditional font colour (good / bad, see section 2).

### Bar and column charts
- Single colour teal `#0F766E`
- Data labels on, 9 pt, `#475569`
- Value axis **off** for bar charts (the labels carry the values); light gridlines `#E2E8F0` for column charts
- Sort by the measure, descending (except ordered categories such as RFM segments, which sort by name)
- Axis titles off

### Line and combo charts
- Line width 3 px; the main measure in teal and the rolling average or comparison in **amber `#D97706`**
- Legend on, at the top
- Markers off for weekly data (53 points), on for monthly data

### Tables
- Header: `#F1F5F9` background, 10 pt Semibold
- Rows: white with alternating `#F8FAFC` banding
- Horizontal gridlines `#E2E8F0`; no vertical gridlines
- Percentages: 1 decimal place. Currency: `$#,0` (`$#,0.00` for averages).
- **Data bars** (optional): add them to the main measure column in teal at 50% transparency.

### Text boxes (titles, findings)
- No background, no border
- Title 20 pt bold; body 9 to 11 pt

### Tooltips
Every chart has a tooltip with **2 to 4 supporting measures** (listed per page below). Keep
the default tooltip; don't build custom tooltip pages unless you need a chart inside the tooltip.

---

## Page 1: Executive Overview

**Page name (tab):** `1. Executive Overview`
**Business question:** *How is the business performing this quarter, and what is the trend?*

| # | Visual | Type | Title | Fields | Position (x, y, w, h) | Filter |
|---|---|---|---|---|---|---|
| 1 | Header | Text box | **Executive Overview** + subtitle | — | 20, 5, 1240, 70 | — |
| 2 | KPI | Card | Net sales (Q4) | `Sales[Net Sales]` | 20, 80, 236, 95 | Q4 2017 |
| 3 | KPI | Card | Transactions (Q4) | `Sales[Baskets]` | 271, 80, 236, 95 | Q4 2017 |
| 4 | KPI | Card | Avg basket value (Q4) | `Sales[Avg Basket Value]` | 522, 80, 236, 95 | Q4 2017 |
| 5 | KPI | Card | Households (Q4) | `Sales[Households]` | 773, 80, 236, 95 | Q4 2017 |
| 6 | KPI | Card | Discount rate (Q4) | `Sales[Discount Rate %]` | 1024, 80, 236, 95 | Q4 2017 |
| 7 | Delta | Card | Sales vs Q3 | `Sales[Net Sales QoQ %]` | 20, 185, 298, 75 | Q4 2017 |
| 8 | Delta | Card | Transactions vs Q3 | `Sales[Baskets QoQ %]` | 333, 185, 298, 75 | Q4 2017 |
| 9 | Delta | Card | Basket value vs Q3 | `Sales[Avg Basket QoQ %]` | 646, 185, 298, 75 | Q4 2017 |
| 10 | Delta | Card | Discount rate vs Q3 | `Sales[Discount Rate Change pts]` | 959, 185, 298, 75 | Q4 2017 |
| 11 | Trend | Line and clustered column | Weekly net sales and 4-week rolling average (2017) | X: `Date[retail_week]` · Columns: `Net Sales` · Line: `Rolling 4-Week Sales` · Tooltips: `Baskets`, `Avg Basket Value`, `WoW Growth %` | 20, 275, 820, 425 | none (full year) |
| 12 | Detail | Table | Quarter detail | `Date[quarter_name]`, `Net Sales`, `Net Sales QoQ %`, `Baskets`, `Avg Basket Value` | 855, 275, 405, 425 | none |

**Subtitle text:** *"Merchandise sales of 2,469 loyalty-panel households, 2017 (fuel and gift cards excluded). KPI cards show Q4 2017; the trend shows the full year."*

**Design details**
- Columns in teal; the rolling-average line in **amber**, 3 px.
- Delta cards: conditional font colour (green up, red down; **reversed for the discount rate**).
- Quarter table: add data bars on `Net Sales`.
- Expected values: Q4 net sales $1,100,662 · 35,428 transactions · $31.07 basket value · discount rate 15.1% · sales +6.2% vs Q3 · basket value +7.4%.

**Talking point:** "Q4 growth came from bigger baskets, not more trips."

---

## Page 2: Customer Analytics

**Page name:** `2. Customer Analytics`
**Business question:** *Which customers drive value, and how loyal are they?*

| # | Visual | Type | Title | Fields | Position | Filter |
|---|---|---|---|---|---|---|
| 1 | Header | Text box | **Customer Analytics** + subtitle | — | 20, 5, 1240, 70 | — |
| 2 | KPI | Card | Shopping households | `Households` | 20, 80, 298, 95 | — |
| 3 | KPI | Card | Households with 2+ trips | `Repeat Household Rate %` | 333, 80, 298, 95 | — |
| 4 | KPI | Card | Trips per household | `Baskets per Household` | 646, 80, 298, 95 | — |
| 5 | KPI | Card | Sales from top 10% of households | `Top 10% Household Share` | 959, 80, 298, 95 | — |
| 6 | Segments | Clustered bar | Share of sales by RFM segment | Y: `Household[rfm_segment]` · X: `Segment Sales Share %` · Tooltips: `Households`, `Sales per Household`, `Baskets per Household` | 20, 190, 620, 270 | — |
| 7 | Segments | Table | RFM segment detail | `rfm_segment`, `Households`, `Sales per Household`, `Baskets per Household`, `Segment Sales Share %` | 655, 190, 605, 270 | — |
| 8 | Income | Clustered column | Annual sales per household by income band (surveyed households) | X: `Household[income_band]` · Y: `Sales per Household` · Tooltips: `Households`, `Private Label Share %` | 20, 475, 620, 225 | `has_demographics` = TRUE |
| 9 | Composition | Clustered bar | Annual sales per household by composition (surveyed households) | Y: `Household[household_comp]` · X: `Sales per Household` · Tooltips: `Households`, `Avg Basket Value` | 655, 475, 605, 225 | `has_demographics` = TRUE |

**Subtitle:** *"RFM segments use recency, frequency and spend quintiles (snapshot 2018-01-01). Demographics exist for 801 of 2,469 households."*

**Design details**
- RFM bar: sort by **segment name ascending** (the names start "1." to "6." so they read in order). Optionally colour "1. Champions" teal and "3. At risk" amber using Format → Bars → Colors → per-category.
- Income chart: sort the X axis by income order. In Data view, set `income_band` → Sort by column if you add an order column, or keep the measure sort.
- Expected values: Champions 513 households, 45.7% of sales · At risk 318 households, 13.4% · top 10% = 34.2%.

**Talking point:** "21% of households, the Champions, generate 46% of sales."

---

## Page 3: Product Analytics

**Page name:** `3. Product Analytics`
**Business question:** *What sells, how widely, and what is bought together?*

| # | Visual | Type | Title | Fields | Position |
|---|---|---|---|---|---|
| 1 | Header | Text box | **Product Analytics** + subtitle | — | 20, 5, 1240, 70 |
| 2 | Departments | Clustered bar | Net sales by department | Y: `Product[department]` · X: `Net Sales` · Tooltips: `Category Sales Share %`, `Product Penetration %`, `Private Label Share %`, `Discount Rate %` | 20, 80, 500, 340 |
| 3 | Categories | Table | Top categories: contribution and reach | `product_category`, `department`, `Net Sales`, `Category Sales Share %`, `Product Penetration %`, `Private Label Share %` | 535, 80, 725, 340 |
| 4 | Affinity | Table | Categories bought together (lift > 1 = more often than chance) | `Basket Affinity[category_a]`, `[category_b]`, `Affinity Lift`, `baskets_together`, `support_pct` | 20, 435, 760, 265 |
| 5 | Types | Table | Top product types | `Product[product_type]`, `Net Sales`, `Households` | 795, 435, 465, 265 |

**Subtitle:** *"Right-click a department and choose Drill through > Department Detail. The source has no product names; product_type is the most specific label."*

**Design details**
- Department bar: top 10 departments. Filter pane → Product[department] → Top N = 10 by `Net Sales`.
- Categories table: data bars on `Net Sales`; a teal colour scale on `Product Penetration %` (white to `#0F766E`).
- Affinity table: sort by `Affinity Lift` descending, with a background colour scale on lift.
- Expected values: Grocery $2,316,394 (55.2% of sales, 99.6% penetration) · top pair Onions + Potatoes lift 4.59.

**Talking point:** "Onions, potatoes and tomatoes are bought together 4.5 times more than chance, a meal-bundle opportunity."

---

## Page 4: Promotion Effectiveness

**Page name:** `4. Promotion Effectiveness`
**Business question:** *Do discounts, coupons and promotions drive extra sales, or only discount existing ones?*

| # | Visual | Type | Title | Fields | Position |
|---|---|---|---|---|---|
| 1 | Header | Text box | **Promotion Effectiveness** + subtitle | — | 20, 5, 1240, 70 |
| 2 | KPI | Card | Sales sold on loyalty discount | `Promo Sales Share %` | 20, 80, 298, 95 |
| 3 | KPI | Card | Retailer discount rate | `Discount Rate %` | 333, 80, 298, 95 |
| 4 | KPI | Card | Coupon redemptions by existing buyers | `Habitual Redemption %` | 646, 80, 298, 95 |
| 5 | KPI | Card | Coupon redemptions scored | `Scored Redemptions` | 959, 80, 298, 95 |
| 6 | Deal segments | Clustered bar | Share of sales by deal dependence | Y: `Household[deal_segment]` · X: `Segment Sales Share %` · Tooltips: `Households`, `Sales per Household` | 20, 190, 410, 250 |
| 7 | Coupons | Clustered column | Coupon redemptions by existing buyers, by campaign type | X: `Coupon Redemptions[campaign_type]` · Y: `Habitual Redemption %` · Tooltips: `Scored Redemptions`, `Habitual Redemptions` | 445, 190, 400, 250 |
| 8 | Lift | Clustered column | Sales lift vs same product and store, unpromoted weeks | X: `Promotion Lift[promotion]` · Y: `Promotion Lift %` · Tooltips: `Lift CI Low %`, `Lift CI High %` | 860, 190, 400, 250 |
| 9 | Campaign test | Table | Campaign impact test (difference-in-differences)… | `Campaign Tests[campaign_type]`, `test`, `effect_per_household_week`, `ci_low`, `ci_high`, `p_value`, `significant` | 20, 455, 1240, 245 |

**Subtitle:** *"Discounts, coupons and in-store promotions. Promotion lift is an association (upper bound); campaign tests show whether an effect can be identified."*

**Design details**
- **Lift chart:** add **error bars** (Format → Analytics → Error bars) with upper = `Lift CI High %` and lower = `Lift CI Low %` to show the 95% CI. Keep the bars teal.
- **Campaign table, so the failed placebo is visible at a glance:**
  - `significant`: conditional background **amber `#FEF3C7`** when TRUE on "Placebo (pre-launch)" rows.
  - `p_value`: 4 decimals.
  - `effect_per_household_week`: font colour red when negative, green when positive.
- **Caption** (text box, 9 pt slate, under the table): *"A significant placebo means targeted households were already trending differently before launch, so the launch effect is not a causal estimate."*
- Expected values: 46.8% of sales on loyalty discount · 50.6% habitual redemptions (Type A 54.5%) · lift: both +225%, mailer +131%, display +129%.

**Talking point:** "Half of coupon redemptions go to people who were already buying, and the campaign test shows why ROI can't be measured yet."

---

## Page 5: Business Recommendations

**Page name:** `5. Business Recommendations`
**Business question:** *What should management do, and how sure can we be?*

| # | Visual | Type | Content | Position |
|---|---|---|---|---|
| 1 | Header | Text box | **Business Recommendations** + subtitle | 20, 5, 1240, 60 |
| 2 | Finding 1 | Text box | A small group of households drives most of the sales | 20, 70, 610, 205 |
| 3 | Finding 2 | Text box | About half of coupon redemptions go to households already buying the product | 650, 70, 610, 205 |
| 4 | Finding 3 | Text box | The data cannot show whether campaigns increase spending | 20, 285, 610, 205 |
| 5 | Finding 4 | Text box | A display and a mailer together are linked to much higher sales than either alone | 650, 285, 610, 205 |
| 6 | Finding 5 | Text box | Fresh-produce and meal-ingredient categories are bought together | 20, 500, 610, 205 |
| 7 | Limitations | Text box | Limitations (panel data, one year, no costs, not randomised, demographics coverage) | 650, 500, 610, 205 |

**Each finding box has the same structure:**

```text
1. <Finding title>                         12pt bold teal
<Evidence sentence with the numbers>        9pt ink
Action: <recommendation>                    "Action:" bold
Caveat: <caveat>                            "Caveat:" bold, text slate
Confidence: <level>                         "Confidence:" bold, text slate
```

The text comes from `reports/findings.json`. Copy it from `reports/findings.md` if you
rebuild these boxes by hand, and don't retype numbers.

**Design details**
- For a "card" look, give each text box a white background, a `#E2E8F0` border and 8 px rounded corners (Format → Effects).
- Add a **4 px left accent bar** per finding (a thin rectangle shape) coloured by confidence:
  - teal `#0F766E` for High
  - amber `#D97706` for Moderate
  - grey `#94A3B8` for "Cannot conclude"
- Optional: an icon per finding (Insert → Shapes, or Unicode: 👥 customers, 🎟️ coupons, 🎯 campaigns, 🏷️ promotions, 🧺 basket).

---

## Department Detail (drill-through)

**Page name:** `Department Detail`
**Purpose:** a focused view of one department, reached from Product Analytics.

| # | Visual | Type | Title | Fields | Position |
|---|---|---|---|---|---|
| 1 | Header | Text box | **Department Detail** + subtitle | — | 20, 5, 1240, 60 |
| 2–6 | KPIs | Card x 5 | Net sales · Share of all sales · Households buying · Own-brand share · Discount rate | `Net Sales`, `Category Sales Share %`, `Product Penetration %`, `Private Label Share %`, `Discount Rate %` | y = 70, h = 95, five equal widths |
| 7 | Trend | Line | Weekly net sales | X: `Date[retail_week]` · Y: `Net Sales` · Tooltips: `Baskets`, `Households` | 20, 180, 620, 520 |
| 8 | Categories | Table | Categories in this department | `product_category`, `Net Sales`, `Product Penetration %`, `Private Label Share %`, `Discount Rate %` | 655, 180, 605, 520 |

**Drill-through set-up:** Drill-through field = `Product[department]`. Keep "Keep all filters" on.
**Add a Back button:** Insert → Buttons → Back. Place it at 1180, 15, 80, 32, with teal icon and white fill.

---

## 12. Step-by-step build guide

### Step 0: Before you start
1. Run `python -m retail.pipeline` so `powerbi/data/*.parquet` is current.
2. Open `powerbi/Retail_Analytics.pbip` in Power BI Desktop.
3. Check the data path: **Transform data → Edit parameters → DataFolder** = your `powerbi\data\` folder, then **Refresh**.
4. **Important:** once you design by hand, **don't run `powerbi/tools/build_report.py`**. It regenerates all pages and would overwrite your design.

### Step 1: Apply the theme
1. **View → Themes → Browse for themes**.
2. Select `powerbi/theme/grocery_retail_theme.json`.
3. All charts, cards, tables and page backgrounds pick up the palette and fonts. Visuals with manual overrides keep those overrides; reset them with Format → **Reset to default** if they look off.

### Step 2: Set every page canvas
For each page: **Format page → Canvas settings → Type 16:9 (1280 x 720)**, and **Canvas background → Color `#F8FAFC`, transparency 0%**.

### Step 3: Turn on the grid
**View → Gridlines** on, **Snap to grid** on. Use **Format → Align / Distribute** to line up KPI cards.

### Step 4: Add page navigation (header)
1. **Insert → Buttons → Navigator → Page navigator**.
2. Place it at the top right (x 760, y 20, w 500, h 32) on every page (copy and paste keeps the position).
3. Format it:
   - Default: text `#475569`, fill white, border `#E2E8F0`.
   - Selected: fill teal `#0F766E`, text white.
   - Font 9 pt, rounded corners 6 px.
4. Hide `Department Detail` from the navigator (Navigator → Pages → turn off Show hidden pages) and from the tab bar (right-click the tab → **Hide page**).

### Step 5: Build or adjust each page
Follow the tables in sections 6 to 11, top to bottom:
1. **Header:** Insert → Text box. Title 20 pt bold; subtitle on a new line, 10 pt, `#475569`.
2. **KPI cards:**
   1. Insert → **Card**.
   2. Drag the measure in.
   3. Format → **Title** on, with the label text.
   4. Callout value 22 to 26 pt teal.
   5. Copy and paste for the other cards, then swap the measure.
3. **Q4 filter on cards (Page 1):**
   1. Select the card.
   2. Filters pane → **Filters on this visual** → drag `Date[quarter_name]` in.
   3. Basic filtering → tick **Q4 2017**.
4. **Charts:**
   1. Insert the chart type, then drag fields into the wells shown in the tables.
   2. Format → Data labels on.
   3. Bars: Format → **Bars → Color** teal.
   4. Sort: the chart's **… → Sort axis**.
5. **Tooltips:** select the chart → in the **Tooltips** field well, drag the measures listed for it.
6. **Tables:** Insert → **Table** → add the columns. Format → Style presets → **Minimal**, then apply the header and row colours from section 5.

### Step 6: Conditional formatting
1. **Delta cards (green/red):**
   1. Select the card → Format → **Callout value → Color → fx**.
   2. Format style **Rules**, based on the card's measure.
   3. If value **>= 0** then `#15803D`; if **< 0** then `#B91C1C`.
   4. For **Discount rate vs Q3**, reverse the colours.
2. **Data bars:** table → column dropdown in the Values well → **Conditional formatting → Data bars**, positive bar `#0F766E`, transparency 50%.
3. **Colour scale:** **Conditional formatting → Background color → Gradient**, minimum white, maximum `#99F6E4`.
4. **Placebo highlight (Page 4):** `significant` column → Background color → Rules → if value = **True** then `#FEF3C7`.

### Step 7: Error bars on the lift chart (Page 4)
Select the lift chart → **Analytics pane (magnifying glass) → Error bars → Enable** → Upper bound `Lift CI High %`, Lower bound `Lift CI Low %` → bar colour `#0F172A`, width 2.

### Step 8: Drill-through (Department Detail)
1. Open the `Department Detail` page → **Visualizations → Build → Drill through** → drag `Product[department]` into the drill-through well. (It's already set up; just check it.)
2. Insert → Buttons → **Back**, top right.
3. Test it: on Product Analytics, right-click a department bar → **Drill through → Department Detail**.

### Step 9: Interactions
On Page 1: **Format → Edit interactions**, and set the KPI cards to **None** for the trend chart, so clicking a week doesn't blank the Q4 cards. Elsewhere, keep cross-filtering on (it's useful for segments).

### Step 10: Accessibility and tab order
1. Each visual → Format → General → **Alt text**: one sentence on what it shows (for example "Bar chart of share of sales by RFM segment; Champions 45.7%").
2. **View → Selection pane → Tab order**: header → KPIs left to right → main chart → table.

### Step 11: Save and verify
1. **Ctrl+S** (the project saves to the PBIP folders).
2. If you changed or added measures, re-run the reconciliation (ask me, or update `reports/powerbi_dax_results.json` and run `python -m retail.reconcile`).
3. `pytest -q` must still pass.

---

## 13. Final quality checklist

- [ ] Every page title is the business question it answers
- [ ] Theme applied; canvas `#F8FAFC`; every visual white with a `#E2E8F0` border and 8 px corners
- [ ] Only teal and amber used as strong colours; red and green only for change indicators
- [ ] KPI cards on Page 1 filtered to Q4 2017; the trend shows the full year
- [ ] Discount-rate delta uses reversed colours (down = green)
- [ ] All percentages 1 decimal; currency `$#,0`; averages `$#,0.00`
- [ ] Every chart has a tooltip with 2 to 4 supporting measures
- [ ] Lift chart has 95% CI error bars; the campaign table highlights significant placebos
- [ ] Demographic visuals filtered to surveyed households and say so in the title
- [ ] Recommendations page: 5 findings with Action, Caveat and Confidence, plus a Limitations box
- [ ] Drill-through works from Product Analytics, and the Back button works
- [ ] Department Detail hidden from the tab bar and navigator
- [ ] Alt text on every visual; tab order set
- [ ] Numbers match the expected values listed per page (and `reports/reconciliation.md`)
- [ ] Saved (Ctrl+S); `pytest -q` passes

---

## 14. Screenshots for the README

1. **File → Export → Export to PDF** (whole report), or take a screenshot of each page at 100% zoom with the Filters and Visualizations panes **collapsed**.
2. Save the screenshots as:

| Page | File |
|---|---|
| Executive Overview | `docs/images/powerbi_1_executive_overview.png` |
| Customer Analytics | `docs/images/powerbi_2_customer_analytics.png` |
| Product Analytics | `docs/images/powerbi_3_product_analytics.png` |
| Promotion Effectiveness | `docs/images/powerbi_4_promotion_effectiveness.png` |
| Business Recommendations | `docs/images/powerbi_5_business_recommendations.png` |

3. Optionally save the PDF as `docs/Retail_Analytics_report.pdf`, so reviewers without Power BI can see every page.
4. Tell me when they're saved, and I'll put the Executive Overview at the top of the README with the others in a gallery.
