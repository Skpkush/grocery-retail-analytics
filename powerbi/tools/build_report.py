"""Generate the Power BI report (PBIR) for Retail_Analytics.pbip.

Report-as-code: every page, visual, binding, tooltip, filter and format is
declared here, following docs/powerbi_design_guide.md, so the report is
reviewable in a diff and rebuilds identically. The Business Recommendations
page and the lift CI subtitle are generated from reports/*.json, the same
sources as the README and the app, so no number is typed by hand.

    python powerbi/tools/build_report.py

Warning: this regenerates every page. Do not run it after designing by hand
in Power BI Desktop, or the manual design will be overwritten.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "powerbi" / "Retail_Analytics.Report"
DEFINITION = REPORT_DIR / "definition"
FINDINGS_PATH = ROOT / "reports" / "findings.json"
STATS_PATH = ROOT / "reports" / "stats_results.json"
CUSTOM_THEME = ROOT / "powerbi" / "theme" / "grocery_retail_theme.json"
BASE_THEME = "CY26SU04"
BASE_THEME_SOURCE = Path(r"C:\Program Files\Microsoft Power BI Desktop\bin\WebView2Resources"
                         rf"\minerva\sharedresources\BaseThemes\{BASE_THEME}.json")
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"

# Design-guide palette (section 2)
TEAL, TEAL_100, AMBER = "#0F766E", "#CCFBF1", "#D97706"
INK, SLATE, MUTED, BORDER = "#0F172A", "#475569", "#94A3B8", "#E2E8F0"
WHITE, CANVAS, HEADER_BAND = "#FFFFFF", "#F8FAFC", "#F1F5F9"
GRADIENT_MAX = "#99F6E4"


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# --- fields, literals, filters --------------------------------------------------

def measure(name: str, table: str = "Sales") -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def column(table: str, name: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def ref(field: dict) -> str:
    kind = "Measure" if "Measure" in field else "Column"
    return f"{field[kind]['Expression']['SourceRef']['Entity']}.{field[kind]['Property']}"


# Friendly column headers ("Rename for this visual"); measures already have business names.
DISPLAY_NAMES = {
    "quarter_name": "Quarter", "rfm_segment": "RFM segment", "deal_segment": "Deal segment",
    "product_category": "Category", "department": "Department", "product_type": "Product type",
    "category_a": "Category A", "category_b": "Category B", "baskets_together": "Baskets together",
    "support_pct": "Support %", "campaign_type": "Campaign type", "test": "Test",
    "effect_per_household_week": "Effect ($/household/week)", "ci_low": "95% CI low",
    "ci_high": "95% CI high", "p_value": "p-value", "significant": "Significant",
    "income_band": "Income band", "household_comp": "Household composition", "retail_week": "Retail week",
    "promotion": "Promotion",
}


def projection(field: dict) -> dict:
    kind = "Measure" if "Measure" in field else "Column"
    prop = field[kind]["Property"]
    out = {"field": field, "queryRef": ref(field), "nativeQueryRef": prop}
    if prop in DISPLAY_NAMES:
        out["displayName"] = DISPLAY_NAMES[prop]
    return out


def lit(value) -> dict:
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (int, float)):
        text = f"{value}D"
    else:
        text = f"'{value}'"
    return {"expr": {"Literal": {"Value": text}}}


def color(hex_value: str) -> dict:
    return {"solid": {"color": lit(hex_value)}}


def color_from(field: dict) -> dict:
    """Conditional colour: 'field value' formatting driven by a colour measure."""
    return {"solid": {"color": {"expr": field}}}


def gradient(field: dict) -> dict:
    """White-to-teal background scale on a numeric column (design guide, step 6)."""
    return {"solid": {"color": {"expr": {"FillRule": {
        "Input": field,
        "FillRule": {"linearGradient2": {
            "min": {"color": {"Literal": {"Value": f"'{WHITE}'"}}},
            "max": {"color": {"Literal": {"Value": f"'{GRADIENT_MAX}'"}}},
            "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}},
        }},
    }}}}}


ALL_POINTS = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}


def in_filter(name: str, table: str, field: str, values: list, alias: str) -> dict:
    def literal(v):
        return "true" if v is True else ("false" if v is False else f"'{v}'")
    return {
        "name": name, "field": column(table, field), "type": "Categorical",
        "filter": {"Version": 2, "From": [{"Name": alias, "Entity": table, "Type": 0}],
                   "Where": [{"Condition": {"In": {
                       "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": alias}},
                                                   "Property": field}}],
                       "Values": [[{"Literal": {"Value": literal(v)}}] for v in values]}}}]},
    }


def q4() -> dict:
    return in_filter("Q4", "Date", "quarter_name", ["Q4 2017"], "d")


def surveyed() -> dict:
    return in_filter("Surveyed", "Household", "has_demographics", [True], "h")


# --- container formatting (title, background, border, alt text) -----------------

def container(title: str | None, alt: str, subtitle: str | None = None, *, background: str | None = WHITE,
              border: bool = True, radius: int = 8, padding: int | None = None) -> dict:
    objs: dict = {"general": [{"properties": {"altText": lit(alt)}}]}
    if title:
        objs["title"] = [{"properties": {"show": lit(True), "text": lit(title), "fontSize": lit(12),
                                         "fontColor": color(INK), "fontFamily": lit("Segoe UI Semibold"),
                                         "alignment": lit("left"), "titleWrap": lit(True)}}]
    else:
        objs["title"] = [{"properties": {"show": lit(False)}}]
    if subtitle:
        objs["subTitle"] = [{"properties": {"show": lit(True), "text": lit(subtitle), "fontSize": lit(9),
                                            "fontColor": color(SLATE), "titleWrap": lit(True)}}]
    if background is None:
        objs["background"] = [{"properties": {"show": lit(False)}}]
    else:
        objs["background"] = [{"properties": {"show": lit(True), "color": color(background),
                                               "transparency": lit(0)}}]
    objs["border"] = [{"properties": {"show": lit(border), "color": color(BORDER), "radius": lit(radius)}}]
    objs["dropShadow"] = [{"properties": {"show": lit(False)}}]
    if padding is not None:
        objs["padding"] = [{"properties": {k: lit(padding) for k in ("top", "bottom", "left", "right")}}]
    return objs


# --- pages and visuals ------------------------------------------------------------

class Page:
    def __init__(self, name, display, filters=None, binding=None, hidden=False):
        self.name, self.display, self.filters, self.binding, self.hidden = name, display, filters or [], binding, hidden
        self.visuals, self.interactions = [], []

    def add(self, name, x, y, w, h, visual, filters=None):
        container_json = {
            "$schema": f"{SCHEMA}/item/report/definition/visualContainer/1.0.0/schema.json",
            "name": name,
            "position": {"x": x, "y": y, "z": len(self.visuals) * 1000, "width": w, "height": h,
                         "tabOrder": len(self.visuals) * 1000},
            "visual": visual,
        }
        if filters:
            container_json["filterConfig"] = {"filters": filters}
        self.visuals.append(container_json)

    def no_filter(self, source: str, targets: list[str]):
        self.interactions += [{"source": source, "target": t, "type": "NoFilter"} for t in targets]

    def save(self):
        page_dir = DEFINITION / "pages" / self.name
        page = {"$schema": f"{SCHEMA}/item/report/definition/page/1.0.0/schema.json",
                "name": self.name, "displayName": self.display, "displayOption": "FitToPage",
                "height": 720, "width": 1280,
                "objects": {"background": [{"properties": {"color": color(CANVAS), "transparency": lit(0)}}],
                            "outspace": [{"properties": {"color": color(CANVAS)}}]}}
        if self.filters:
            page["filterConfig"] = {"filters": self.filters}
        if self.binding:
            page["pageBinding"] = self.binding
        if self.hidden:
            page["visibility"] = "HiddenInViewMode"
        if self.interactions:
            page["visualInteractions"] = self.interactions
        write(page_dir / "page.json", page)
        for v in self.visuals:
            write(page_dir / "visuals" / v["name"] / "visual.json", v)


def run(text: str, size: str = "10pt", bold: bool = False, colour: str = INK) -> dict:
    style = {"fontSize": size, "color": colour, "fontFamily": "Segoe UI"}
    if bold:
        style["fontWeight"] = "bold"
    return {"value": text, "textStyle": style}


def textbox(paragraphs: list[list[dict]], alt: str, *, card: bool = False, background: str | None = None) -> dict:
    if card:
        objs = container(None, alt, background=WHITE, border=True, radius=8, padding=12)
    else:
        objs = container(None, alt, background=background, border=False, radius=0, padding=0)
    return {"visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": r} for r in paragraphs]}}]},
            "visualContainerObjects": objs}


def heading(text: str, sub: str) -> dict:
    return textbox([[run(text, "20pt", bold=True)], [run(sub, "10pt", colour=SLATE)]],
                   alt=f"Page title: {text}. {sub}")


MILLIONS_MEASURES = {"Net Sales"}  # shown as $1.10M; everything else unabbreviated


def card(field: dict, label: str, *, font: int = 24, value_color: dict | None = None) -> dict:
    name = field.get("Measure", {}).get("Property", "")
    units, precision = (1_000_000, 2) if name in MILLIONS_MEASURES else (1, None)
    labels = {"fontSize": lit(font), "color": value_color or color(TEAL),
              "fontFamily": lit("Segoe UI Semibold"), "labelDisplayUnits": lit(units)}
    if precision is not None:
        labels["labelPrecision"] = lit(precision)
    return {"visualType": "card",
            "query": {"queryState": {"Values": {"projections": [projection(field)]}}},
            "objects": {"labels": [{"properties": labels}],
                        "categoryLabels": [{"properties": {"show": lit(False)}}]},
            "visualContainerObjects": container(label, f"KPI card: {label}"),
            "drillFilterOtherVisuals": True}


def sort(field: dict, descending: bool) -> dict:
    return {"sort": [{"field": field, "direction": "Descending" if descending else "Ascending"}],
            "isDefaultSort": False}


def chart(kind, category, values, title, *, line=None, tooltips=None, sort_by=None, descending=True,
          subtitle=None, bar_color: dict | None = None, alt: str | None = None) -> dict:
    state = {"Category": {"projections": [projection(category)]},
             "Y": {"projections": [projection(v) for v in values]}}
    if line:
        state["Y2"] = {"projections": [projection(v) for v in line]}
    if tooltips:
        state["Tooltips"] = {"projections": [projection(t) for t in tooltips]}
    query = {"queryState": state}
    if sort_by:
        query["sortDefinition"] = sort(sort_by, descending)
    data_point = [{"properties": {"fill": color(TEAL)}}]
    if bar_color:  # conditional colour per category (field value)
        data_point.append({"properties": {"fill": bar_color}, "selector": ALL_POINTS})
    if line:  # rolling average / comparison series in amber
        data_point += [{"properties": {"fill": color(AMBER)}, "selector": {"metadata": ref(f)}} for f in line]
    labels = {"show": lit(not line), "color": color(SLATE), "fontSize": lit(9)}
    if kind in ("clusteredBarChart", "clusteredColumnChart"):
        labels["labelPosition"] = lit("OutsideEnd")  # never draw a label inside a bar
    objects = {"dataPoint": data_point, "labels": [{"properties": labels}],
               "categoryAxis": [{"properties": {"showAxisTitle": lit(False), "maxMarginFactor": lit(40)}}],
               "valueAxis": [{"properties": {"showAxisTitle": lit(False)}}]}
    if kind == "clusteredBarChart":
        objects["valueAxis"] = [{"properties": {"show": lit(False), "gridlineShow": lit(False),
                                                "showAxisTitle": lit(False)}}]
    if kind in ("lineChart", "lineClusteredColumnComboChart"):
        objects["lineStyles"] = [{"properties": {"strokeWidth": lit(3), "showMarker": lit(False)}}]
        objects["legend"] = [{"properties": {"show": lit(bool(line)), "position": lit("Top")}}]
    return {"visualType": kind, "query": query, "objects": objects,
            "visualContainerObjects": container(title, alt or title, subtitle),
            "drillFilterOtherVisuals": True}


def cell_selector(target: str) -> dict:
    """Per-cell conditional formatting needs a data scope as well as the column."""
    return {**ALL_POINTS, "metadata": target}


def table(fields, title, *, sort_by=None, descending=True, gradients=(), back_colors=None, font_colors=None,
          totals: bool = True, alt: str | None = None) -> dict:
    query = {"queryState": {"Values": {"projections": [projection(f) for f in fields]}}}
    if sort_by:
        query["sortDefinition"] = sort(sort_by, descending)
    values = []
    for f in gradients:
        values.append({"properties": {"backColor": gradient(f)}, "selector": cell_selector(ref(f))})
    for target, colour_measure in (back_colors or {}).items():
        values.append({"properties": {"backColor": color_from(colour_measure)}, "selector": cell_selector(target)})
    for target, colour_measure in (font_colors or {}).items():
        values.append({"properties": {"fontColor": color_from(colour_measure)},
                       "selector": cell_selector(target)})
    objects = {"columnHeaders": [{"properties": {"backColor": color(HEADER_BAND), "fontColor": color(INK),
                                                 "fontFamily": lit("Segoe UI Semibold"), "fontSize": lit(10)}}],
               "grid": [{"properties": {"gridVertical": lit(False), "gridHorizontal": lit(True),
                                        "gridHorizontalColor": color(BORDER)}}]}
    if values:
        objects["values"] = values
    if not totals:
        objects["total"] = [{"properties": {"totals": lit(False)}}]
    return {"visualType": "tableEx", "query": query, "objects": objects,
            "visualContainerObjects": container(title, alt or title), "drillFilterOtherVisuals": True}


def navigator() -> dict:
    """Page navigator buttons (design guide, step 4)."""
    return {"visualType": "pageNavigator",
            "objects": {
                "fill": [{"properties": {"fillColor": color(WHITE), "show": lit(True)},
                          "selector": {"id": "default"}},
                         {"properties": {"fillColor": color(TEAL)}, "selector": {"id": "selected"}}],
                "text": [{"properties": {"fontColor": color(SLATE), "fontSize": lit(8)},
                          "selector": {"id": "default"}},
                         {"properties": {"fontColor": color(WHITE)}, "selector": {"id": "selected"}}],
                "outline": [{"properties": {"show": lit(True), "lineColor": color(BORDER),
                                            "roundEdge": lit(6)}, "selector": {"id": "default"}}],
                "pages": [{"properties": {"showHiddenPages": lit(False)}}],
            },
            "visualContainerObjects": container(None, "Page navigation buttons", background=None, border=False)}


def back_button() -> dict:
    return {"visualType": "actionButton",
            "objects": {"icon": [{"properties": {"show": lit(True), "shapeType": lit("back"),
                                                 "lineColor": color(TEAL), "lineWeight": lit(2)},
                                  "selector": {"id": "default"}}],
                        "text": [{"properties": {"show": lit(True), "text": lit("Back"), "fontColor": color(TEAL),
                                                 "fontSize": lit(10)}, "selector": {"id": "default"}}],
                        "fill": [{"properties": {"show": lit(True), "fillColor": color(WHITE)},
                                  "selector": {"id": "default"}}],
                        "outline": [{"properties": {"show": lit(True), "lineColor": color(BORDER),
                                                    "roundEdge": lit(6)}, "selector": {"id": "default"}}]},
            "visualContainerObjects": {**container(None, "Back to the previous page", background=None,
                                                   border=False, padding=0),
                                       "visualLink": [{"properties": {"show": lit(True), "type": lit("Back")}}]}}


def kpi_row(page: Page, prefix: str, items, y: int, h: int = 95, font: int = 24, filters=None):
    width = (1240 - 15 * (len(items) - 1)) // len(items)
    for i, item in enumerate(items):
        m, label = item[0], item[1]
        colour = item[2] if len(item) > 2 else None
        field = m if isinstance(m, dict) else measure(m)
        page.add(f"{prefix}_{i}", 20 + i * (width + 15), y, width, h,
                 card(field, label, font=font, value_color=color_from(colour) if colour else None),
                 filters=filters)


def add_header(page: Page, title: str, subtitle: str, nav: bool = True, height: int = 70):
    page.add("heading", 20, 5, 520 if nav else 1140, height, heading(title, subtitle))
    if nav:  # 5 buttons x ~141 px fit "4. Promotion Effectiveness" at 8 pt
        page.add("navigation", 555, 18, 705, 34, navigator())


# --- report -------------------------------------------------------------------------

def lift_subtitle() -> str:
    if not STATS_PATH.exists():
        return "Upper bound: promotions are not randomly assigned."
    lift = json.loads(STATS_PATH.read_text(encoding="utf-8")).get("promotion_lift", {})
    parts = [f"{k.lower()} {v['ci95_pct'][0]:.0f}-{v['ci95_pct'][1]:.0f}%" for k, v in lift.items()]
    return "95% CI: " + "; ".join(parts) + ". Upper bound: promotions are not randomly assigned."


def build_pages() -> list[Page]:
    pages = []

    # 1. Executive Overview -------------------------------------------------------
    p = Page("executive_overview", "1. Executive Overview")
    add_header(p, "Executive Overview",
               "Merchandise sales of 2,469 loyalty-panel households, 2017 (fuel and gift cards excluded). "
               "KPI cards show Q4 2017; the trend shows the full year.")
    kpi_row(p, "kpi", [("Net Sales", "Net sales (Q4)"), ("Baskets", "Transactions (Q4)"),
                       ("Avg Basket Value", "Avg basket value (Q4)"), ("Households", "Households (Q4)"),
                       ("Discount Rate %", "Discount rate (Q4)")], 80, filters=[q4()])
    kpi_row(p, "delta", [("Net Sales QoQ %", "Sales vs Q3", measure("Color Sales QoQ")),
                         ("Baskets QoQ %", "Transactions vs Q3", measure("Color Baskets QoQ")),
                         ("Avg Basket QoQ %", "Basket value vs Q3", measure("Color Basket Value QoQ")),
                         ("Discount Rate Change pts", "Discount rate vs Q3", measure("Color Discount Change"))],
            185, h=75, font=16, filters=[q4()])
    p.add("weekly", 20, 275, 820, 425, chart(
        "lineClusteredColumnComboChart", column("Date", "retail_week"), [measure("Net Sales")],
        "Weekly net sales and 4-week rolling average (2017)", line=[measure("Rolling 4-Week Sales")],
        tooltips=[measure("Baskets"), measure("Avg Basket Value"), measure("WoW Growth %")],
        sort_by=column("Date", "retail_week"), descending=False,
        alt="Combo chart of weekly net sales (teal columns) with a 4-week rolling average (amber line) for 2017."))
    p.add("quarters", 855, 275, 405, 425, table(
        [column("Date", "quarter_name"), measure("Net Sales"), measure("Net Sales QoQ %"),
         measure("Baskets"), measure("Avg Basket Value")],
        "Quarter detail", sort_by=column("Date", "quarter_name"), descending=False,
        gradients=[measure("Net Sales")], totals=False,
        alt="Table of net sales, growth, transactions and basket value by quarter."))
    cards = [f"kpi_{i}" for i in range(5)] + [f"delta_{i}" for i in range(4)]
    p.no_filter("weekly", cards)  # clicking a week must not blank the Q4 cards
    p.no_filter("quarters", cards)
    pages.append(p)

    # 2. Customer Analytics -------------------------------------------------------
    p = Page("customer_analytics", "2. Customer Analytics")
    add_header(p, "Customer Analytics",
               "RFM segments use recency, frequency and spend quintiles (snapshot 2018-01-01). "
               "Demographics exist for 801 of 2,469 households.")
    kpi_row(p, "kpi", [("Households", "Shopping households"),
                       ("Repeat Household Rate %", "Households with 2+ trips"),
                       ("Baskets per Household", "Trips per household"),
                       ("Top 10% Household Share", "Sales from top 10% of households")], 80)
    p.add("rfm_bar", 20, 190, 620, 270, chart(
        "clusteredBarChart", column("Household", "rfm_segment"), [measure("Segment Sales Share %")],
        "Share of sales by RFM segment",
        subtitle="Champions (teal) and At risk (amber) highlighted",
        tooltips=[measure("Households"), measure("Sales per Household"), measure("Baskets per Household")],
        sort_by=column("Household", "rfm_segment"), descending=False, bar_color=color_from(measure("Color RFM Segment")),
        alt="Bar chart of share of sales by RFM segment; Champions hold the largest share."))
    p.add("rfm_table", 655, 190, 605, 270, table(
        [column("Household", "rfm_segment"), measure("Households"), measure("Sales per Household"),
         measure("Baskets per Household"), measure("Segment Sales Share %")],
        "RFM segment detail", sort_by=column("Household", "rfm_segment"), descending=False,
        gradients=[measure("Segment Sales Share %")]))
    p.add("income", 20, 475, 620, 225, chart(
        "clusteredColumnChart", column("Household", "income_band"), [measure("Sales per Household")],
        "Annual sales per household by income band (surveyed households)",
        tooltips=[measure("Households"), measure("Private Label Share %")],
        sort_by=measure("Sales per Household")), filters=[surveyed()])
    p.add("composition", 655, 475, 605, 225, chart(
        "clusteredBarChart", column("Household", "household_comp"), [measure("Sales per Household")],
        "Annual sales per household by composition (surveyed households)",
        tooltips=[measure("Households"), measure("Avg Basket Value")],
        sort_by=measure("Sales per Household")), filters=[surveyed()])
    pages.append(p)

    # 3. Product Analytics ------------------------------------------------------
    p = Page("product_analytics", "3. Product Analytics")
    add_header(p, "Product Analytics",
               "Right-click a department > Drill through > Department Detail. The source has no product "
               "names; product_type is the most specific label.")
    p.add("departments", 20, 80, 500, 340, chart(
        "clusteredBarChart", column("Product", "department"), [measure("Net Sales")],
        "Net sales by department", subtitle="Right-click a bar to drill through",
        tooltips=[measure("Category Sales Share %"), measure("Product Penetration %"),
                  measure("Private Label Share %"), measure("Discount Rate %")],
        sort_by=measure("Net Sales")))
    p.add("categories", 535, 80, 725, 340, table(
        [column("Product", "product_category"), column("Product", "department"), measure("Net Sales"),
         measure("Category Sales Share %"), measure("Product Penetration %"),
         measure("Private Label Share %")],
        "Top categories: contribution and reach", sort_by=measure("Net Sales"),
        gradients=[measure("Net Sales"), measure("Product Penetration %")]))
    p.add("affinity", 20, 435, 760, 265, table(
        [column("Basket Affinity", "category_a"), column("Basket Affinity", "category_b"),
         measure("Affinity Lift", "Basket Affinity"), column("Basket Affinity", "baskets_together"),
         column("Basket Affinity", "support_pct")],
        "Categories bought together (lift > 1 = more often than chance)",
        sort_by=measure("Affinity Lift", "Basket Affinity"), totals=False,
        gradients=[measure("Affinity Lift", "Basket Affinity")]))
    p.add("types", 795, 435, 465, 265, table(
        [column("Product", "product_type"), measure("Net Sales"), measure("Households")],
        "Top product types", sort_by=measure("Net Sales"), gradients=[measure("Net Sales")]))
    pages.append(p)

    # 4. Promotion Effectiveness ------------------------------------------------
    p = Page("promotion_effectiveness", "4. Promotion Effectiveness")
    add_header(p, "Promotion Effectiveness",
               "Discounts, coupons and in-store promotions. Lift is an association (upper bound); "
               "campaign tests show whether an effect can be identified.")
    kpi_row(p, "kpi", [("Promo Sales Share %", "Sales sold on loyalty discount"),
                       ("Discount Rate %", "Retailer discount rate"),
                       ("Habitual Redemption %", "Coupon redemptions by existing buyers"),
                       ("Scored Redemptions", "Coupon redemptions scored")], 80)
    p.add("deal", 20, 190, 410, 235, chart(
        "clusteredBarChart", column("Household", "deal_segment"), [measure("Segment Sales Share %")],
        "Share of sales by deal dependence",
        tooltips=[measure("Households"), measure("Sales per Household")],
        sort_by=column("Household", "deal_segment"), descending=False))
    p.add("habitual", 445, 190, 400, 235, chart(
        "clusteredColumnChart", column("Coupon Redemptions", "campaign_type"),
        [measure("Habitual Redemption %")], "Coupon redemptions by existing buyers, by campaign type",
        tooltips=[measure("Scored Redemptions"), measure("Habitual Redemptions")],
        sort_by=column("Coupon Redemptions", "campaign_type"), descending=False))
    p.add("lift", 860, 190, 400, 235, chart(
        "clusteredColumnChart", column("Promotion Lift", "promotion"),
        [measure("Promotion Lift %", "Promotion Lift")],
        "Sales lift vs same product and store, unpromoted weeks", subtitle=lift_subtitle(),
        tooltips=[measure("Lift CI Low %", "Promotion Lift"), measure("Lift CI High %", "Promotion Lift")],
        sort_by=measure("Promotion Lift %", "Promotion Lift")))
    p.add("tests", 20, 440, 1240, 237, table(
        [column("Campaign Tests", "campaign_type"), column("Campaign Tests", "test"),
         column("Campaign Tests", "effect_per_household_week"), column("Campaign Tests", "ci_low"),
         column("Campaign Tests", "ci_high"), column("Campaign Tests", "p_value"),
         column("Campaign Tests", "significant")],
        "Campaign impact test (difference-in-differences, $ per household per week)",
        sort_by=column("Campaign Tests", "campaign_type"), descending=False, totals=False,
        back_colors={"Campaign Tests.significant": measure("Color Placebo Highlight", "Campaign Tests")},
        font_colors={"Campaign Tests.effect_per_household_week": measure("Color Effect", "Campaign Tests")}))
    p.add("caption", 20, 682, 1240, 24, textbox([[run(
        "A significant placebo (amber) means targeted households were already trending differently before "
        "launch, so the launch effect is not a causal estimate.", "9pt", colour=SLATE)]],
        alt="Caption explaining the placebo test"))
    pages.append(p)

    # 5. Business Recommendations -----------------------------------------------
    p = Page("recommendations", "5. Business Recommendations")
    add_header(p, "Business Recommendations",
               "Evidence, action, caveat and confidence per finding. No savings or ROI are claimed.")
    findings = json.loads(FINDINGS_PATH.read_text(encoding="utf-8")) if FINDINGS_PATH.exists() else []
    # (x, y, height): row 2 holds the longest findings, so it gets the most height
    positions = [(20, 76, 198), (650, 76, 198), (20, 282, 226), (650, 282, 226), (20, 516, 186)]
    for i, (f, (x, y, h)) in enumerate(zip(findings, positions, strict=False)):
        conf = f["confidence"].split(":")[0]
        accent = TEAL if conf.startswith("High") else (AMBER if conf.startswith("Moderate") else MUTED)
        p.add(f"accent_{i}", x, y, 5, h, textbox([[run(" ", "6pt")]], alt=f"{conf} confidence marker",
                                                     background=accent))
        p.add(f"finding_{i}", x + 8, y, 602, h, textbox([
            [run(f"{i + 1}. {f['title']}", "12pt", bold=True, colour=TEAL)],
            [run(f["evidence"], "8.5pt")],
            [run("Action: ", "8.5pt", bold=True), run(f["recommendation"], "8.5pt")],
            [run("Caveat: ", "8.5pt", bold=True), run(f["caveat"], "8.5pt", colour=SLATE)],
            [run("Confidence: ", "8.5pt", bold=True), run(conf, "8.5pt", colour=SLATE)],
        ], alt=f"Finding {i + 1}: {f['title']}", card=True))
    p.add("accent_limits", 650, 516, 5, 186, textbox([[run(" ", "6pt")]], alt="Limitations marker",
                                                      background=SLATE))
    p.add("limitations", 658, 516, 602, 186, textbox([
        [run("Limitations", "12pt", bold=True, colour=TEAL)],
        [run("- A loyalty panel of 2,469 households, not total store sales.", "9pt")],
        [run("- One year (2017). No cost or margin data, so no profitability analysis.", "9pt")],
        [run("- Promotions and campaigns are not randomised, so lift is an association.", "9pt")],
        [run("- Demographics cover 32% of households.", "9pt")],
        [run("Confidence bar: teal = high, amber = moderate, grey = cannot conclude.", "9pt", colour=SLATE)],
        [run("Methods and data quality: docs/methodology.md, docs/data_quality.md.", "9pt", colour=SLATE)],
    ], alt="Limitations of the analysis", card=True))
    pages.append(p)

    # 6. Department Detail (drill-through target, hidden from tabs) --------------
    drill_filter = {"name": "DrillDepartment", "field": column("Product", "department"), "type": "Categorical",
                    "howCreated": "Drillthrough"}
    p = Page("department_detail", "Department Detail", filters=[drill_filter], hidden=True, binding={
        "name": "DepartmentDrillthrough", "type": "Drillthrough",
        "parameters": [{"name": "DepartmentParam", "boundFilter": "DrillDepartment",
                        "fieldExpr": column("Product", "department")}]})
    add_header(p, "Department Detail", "Drill-through from Product Analytics. Use the Back button to return.",
               nav=False, height=60)
    p.add("back", 1150, 15, 110, 36, back_button())
    kpi_row(p, "kpi", [("Net Sales", "Net sales"), ("Category Sales Share %", "Share of all sales"),
                       ("Product Penetration %", "Households buying"),
                       ("Private Label Share %", "Own-brand share"), ("Discount Rate %", "Discount rate")], 70)
    p.add("trend", 20, 180, 620, 520, chart(
        "lineChart", column("Date", "retail_week"), [measure("Net Sales")], "Weekly net sales",
        tooltips=[measure("Baskets"), measure("Households")],
        sort_by=column("Date", "retail_week"), descending=False))
    p.add("cats", 655, 180, 605, 520, table(
        [column("Product", "product_category"), measure("Net Sales"), measure("Product Penetration %"),
         measure("Private Label Share %"), measure("Discount Rate %")],
        "Categories in this department", sort_by=measure("Net Sales"), gradients=[measure("Net Sales")]))
    pages.append(p)
    return pages


def main() -> None:
    if DEFINITION.exists():
        for child in DEFINITION.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    write(REPORT_DIR / "definition.pbir", {
        "$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json", "version": "4.0",
        "datasetReference": {"byPath": {"path": "../Retail_Analytics.SemanticModel"}}})
    write(DEFINITION / "version.json", {
        "$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    theme_file = CUSTOM_THEME.name
    write(DEFINITION / "report.json", {
        "$schema": f"{SCHEMA}/item/report/definition/report/1.0.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": BASE_THEME, "reportVersionAtImport": "5.55", "type": "SharedResources"},
            "customTheme": {"name": theme_file, "reportVersionAtImport": "5.55", "type": "RegisteredResources"},
        },
        "layoutOptimization": "None",
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": BASE_THEME, "path": f"BaseThemes/{BASE_THEME}.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": theme_file, "path": theme_file, "type": "CustomTheme"}]},
        ],
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True},
    })
    base_target = REPORT_DIR / "StaticResources" / "SharedResources" / "BaseThemes" / f"{BASE_THEME}.json"
    if not base_target.exists():
        base_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(BASE_THEME_SOURCE, base_target)
    custom_target = REPORT_DIR / "StaticResources" / "RegisteredResources" / theme_file
    custom_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CUSTOM_THEME, custom_target)
    pages = build_pages()
    for page in pages:
        page.save()
    write(DEFINITION / "pages" / "pages.json", {
        "$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p.name for p in pages], "activePageName": pages[0].name})
    print(f"Wrote {len(pages)} pages, {sum(len(p.visuals) for p in pages)} visuals to {DEFINITION}")


if __name__ == "__main__":
    main()
