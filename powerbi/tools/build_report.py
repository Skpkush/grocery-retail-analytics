"""Generate the Power BI report (PBIR) for Retail_Analytics.pbip.

Report-as-code: every page, visual, binding and filter is declared here, so the
report is reviewable in a diff and rebuilds identically. Narrative text on the
campaign page is generated from reports/stats_results.json.

    python powerbi/tools/build_report.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "powerbi" / "Retail_Analytics.Report"
DEFINITION = REPORT_DIR / "definition"
STATS_PATH = ROOT / "reports" / "stats_results.json"
THEME = "CY26SU04"
THEME_SOURCE = Path(r"C:\Program Files\Microsoft Power BI Desktop\bin\WebView2Resources"
                    rf"\minerva\sharedresources\BaseThemes\{THEME}.json")
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
TEAL = "#0F766E"


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def measure(name: str, table: str = "Sales") -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def column(table: str, name: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def projection(field: dict) -> dict:
    kind = "Measure" if "Measure" in field else "Column"
    entity = field[kind]["Expression"]["SourceRef"]["Entity"]
    prop = field[kind]["Property"]
    return {"field": field, "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}


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


def in_filter(name: str, table: str, field: str, values: list, alias: str = "t") -> dict:
    def literal(v):
        return "true" if v is True else ("false" if v is False else f"'{v}'")
    return {
        "name": name,
        "field": column(table, field),
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": alias, "Entity": table, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": alias}}, "Property": field}}],
                "Values": [[{"Literal": {"Value": literal(v)}}] for v in values],
            }}}],
        },
    }


Q4 = in_filter("Quarter", "Date", "quarter_name", ["Q4 2017"], alias="d")
SURVEYED = in_filter("Surveyed", "Household", "has_demographics", [True], alias="h")


class Page:
    def __init__(self, name: str, display: str, filters: list | None = None):
        self.name, self.display, self.filters, self.visuals = name, display, filters or [], []

    def add(self, name, x, y, w, h, visual, filters=None):
        container = {
            "$schema": f"{SCHEMA}/item/report/definition/visualContainer/1.0.0/schema.json",
            "name": name,
            "position": {"x": x, "y": y, "z": len(self.visuals) * 1000, "width": w, "height": h,
                         "tabOrder": len(self.visuals) * 1000},
            "visual": visual,
        }
        if filters:
            container["filterConfig"] = {"filters": filters}
        self.visuals.append(container)

    def save(self):
        page_dir = DEFINITION / "pages" / self.name
        page = {"$schema": f"{SCHEMA}/item/report/definition/page/1.0.0/schema.json",
                "name": self.name, "displayName": self.display, "displayOption": "FitToPage",
                "height": 720, "width": 1280}
        if self.filters:
            page["filterConfig"] = {"filters": self.filters}
        write(page_dir / "page.json", page)
        for v in self.visuals:
            write(page_dir / "visuals" / v["name"] / "visual.json", v)


def title(text: str) -> dict:
    return {"title": [{"properties": {"show": lit(True), "text": lit(text), "fontSize": lit(12)}}]}


def textbox(text: str, size: str = "20pt", bold: bool = True) -> dict:
    style = {"fontSize": size, "color": "#0F172A"}
    if bold:
        style["fontWeight"] = "bold"
    return {"visualType": "textbox", "objects": {"general": [{"properties": {
        "paragraphs": [{"textRuns": [{"value": text, "textStyle": style}]}]}}]}}


def card(field: dict, label: str, font: int = 24) -> dict:
    return {"visualType": "card",
            "query": {"queryState": {"Values": {"projections": [projection(field)]}}},
            "objects": {"labels": [{"properties": {"fontSize": lit(font), "color": color(TEAL)}}],
                        "categoryLabels": [{"properties": {"show": lit(True)}}], **title(label)},
            "drillFilterOtherVisuals": True}


def sort(field: dict, descending: bool) -> dict:
    return {"sort": [{"field": field, "direction": "Descending" if descending else "Ascending"}],
            "isDefaultSort": False}


def chart(kind, category, values, label, line=None, sort_by=None, descending=True) -> dict:
    state = {"Category": {"projections": [projection(category)]},
             "Y": {"projections": [projection(v) for v in values]}}
    if line:
        state["Y2"] = {"projections": [projection(v) for v in line]}
    query = {"queryState": state}
    if sort_by:
        query["sortDefinition"] = sort(sort_by, descending)
    return {"visualType": kind, "query": query,
            "objects": {"dataPoint": [{"properties": {"fill": color(TEAL)}}],
                        "labels": [{"properties": {"show": lit(True)}}], **title(label)},
            "drillFilterOtherVisuals": True}


def table(fields, label, sort_by=None, descending=True) -> dict:
    query = {"queryState": {"Values": {"projections": [projection(f) for f in fields]}}}
    if sort_by:
        query["sortDefinition"] = sort(sort_by, descending)
    return {"visualType": "tableEx", "query": query, "objects": title(label),
            "drillFilterOtherVisuals": True}


def campaign_narrative() -> str:
    if not STATS_PATH.exists():
        return "Run python -m retail.stats to generate the campaign tests."
    s = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    coupon = s["coupon_habitual"]["All"]
    failed = sum(r["placebo"]["p_value"] < 0.05 for r in s["campaign_did"].values())
    return (f"{coupon['habitual_pct']:.1f}% of coupon redemptions (95% CI {coupon['ci95_pct'][0]}-"
            f"{coupon['ci95_pct'][1]}%) came from households already buying the product. "
            f"Campaign lift is not measurable: the difference-in-differences placebo test fails for "
            f"{failed} of {len(s['campaign_did'])} campaign types (targeted households were already "
            "declining before launch). Recommendation: hold out 10% of every target list.")


def build_pages() -> list[Page]:
    overview = Page("overview", "Executive Overview", [Q4])
    overview.add("title", 20, 10, 1000, 50, textbox("Complete Journey 2017 | Q4 business review"))
    overview.add("subtitle", 20, 55, 1200, 30, textbox(
        "Merchandise sales of 2,469 panel households (fuel and gift cards excluded). Quarter is set in "
        "the Filters pane. Measures mirror src/retail/metrics.py.", size="10pt", bold=False))
    for i, (m, label) in enumerate([("Net Sales", "Net sales"), ("Baskets", "Baskets"),
                                    ("Avg Basket Value", "Avg basket"), ("Households", "Households"),
                                    ("Discount Rate %", "Discount rate"),
                                    ("Private Label Share %", "Own-brand share")]):
        overview.add(f"kpi_{i}", 20 + i * 208, 95, 198, 100, card(measure(m), label))
    for i, (m, label) in enumerate([("Net Sales QoQ %", "Sales vs Q3"), ("Baskets QoQ %", "Baskets vs Q3"),
                                    ("Avg Basket QoQ %", "Basket value vs Q3"),
                                    ("Discount Rate Change pts", "Discount rate vs Q3")]):
        overview.add(f"delta_{i}", 20 + i * 208, 205, 198, 80, card(measure(m), label, font=16))
    overview.add("dept_bar", 20, 300, 600, 400, chart(
        "clusteredBarChart", column("Product", "department"), [measure("Net Sales")],
        "Net sales by department", sort_by=measure("Net Sales")))
    overview.add("dept_table", 635, 300, 625, 400, table(
        [column("Product", "department"), measure("Net Sales"), measure("Households"),
         measure("Discount Rate %"), measure("Private Label Share %")],
        "Department scorecard", sort_by=measure("Net Sales")))

    trends = Page("trends", "Trends")
    trends.add("title", 20, 10, 900, 50, textbox("Weekly and quarterly trends"))
    trends.add("weekly", 20, 70, 1240, 330, chart(
        "lineClusteredColumnComboChart", column("Date", "retail_week"), [measure("Net Sales")],
        "Net sales by retail week and 4-week rolling average", line=[measure("Rolling 4-Week Sales")],
        sort_by=column("Date", "retail_week"), descending=False))
    trends.add("basket_month", 20, 415, 620, 285, chart(
        "lineChart", column("Date", "month_name"), [measure("Avg Basket Value")],
        "Average basket value by month", sort_by=column("Date", "month_name"), descending=False))
    trends.add("quarter_table", 655, 415, 605, 285, table(
        [column("Date", "quarter_name"), measure("Net Sales"), measure("Net Sales QoQ %"),
         measure("Baskets"), measure("Avg Basket Value"), measure("Discount Rate %")],
        "Quarter detail", sort_by=column("Date", "quarter_name"), descending=False))

    customers = Page("customers", "Customers")
    customers.add("title", 20, 10, 900, 50, textbox("Customer value and demographics"))
    for i, (m, label) in enumerate([("Households", "Households"),
                                    ("Top 10% Household Share", "Sales from top 10% of households"),
                                    ("Sales per Household", "Sales per household")]):
        customers.add(f"kpi_{i}", 20 + i * 415, 70, 400, 100, card(measure(m), label))
    customers.add("income", 20, 185, 620, 250, chart(
        "clusteredColumnChart", column("Household", "income_band"), [measure("Sales per Household")],
        "Sales per household by income band (surveyed households)",
        sort_by=measure("Sales per Household")), filters=[SURVEYED])
    customers.add("comp", 655, 185, 605, 250, chart(
        "clusteredBarChart", column("Household", "household_comp"), [measure("Sales per Household")],
        "Sales per household by composition (surveyed households)",
        sort_by=measure("Sales per Household")), filters=[SURVEYED])
    customers.add("age", 20, 450, 1240, 250, table(
        [column("Household", "age"), measure("Households"), measure("Sales per Household"),
         measure("Avg Basket Value"), measure("Private Label Share %")],
        "Age group detail (surveyed households)", sort_by=column("Household", "age"), descending=False),
        filters=[SURVEYED])

    campaigns = Page("campaigns", "Campaigns & Coupons")
    campaigns.add("title", 20, 10, 900, 50, textbox("Campaigns and coupons"))
    for i, (m, label) in enumerate([("Targeted Households", "Campaign targets"),
                                    ("Redemptions", "Coupon redemptions"),
                                    ("Household Redemption Rate %", "Household redemption rate")]):
        campaigns.add(f"kpi_{i}", 20 + i * 415, 70, 400, 100, card(measure(m), label))
    campaigns.add("narrative", 20, 180, 1240, 90, textbox(campaign_narrative(), size="11pt", bold=False))
    campaigns.add("rate_by_type", 20, 280, 620, 420, chart(
        "clusteredColumnChart", column("Campaign Targets", "campaign_type"),
        [measure("Household Redemption Rate %")], "Household redemption rate by campaign type",
        sort_by=column("Campaign Targets", "campaign_type"), descending=False))
    campaigns.add("redemptions_by_type", 655, 280, 605, 420, chart(
        "clusteredColumnChart", column("Coupon Redemptions", "campaign_type"), [measure("Redemptions")],
        "Redemptions by campaign type", sort_by=column("Coupon Redemptions", "campaign_type"),
        descending=False))

    brand = Page("own_brand", "Own Brand & Discounts")
    brand.add("title", 20, 10, 900, 50, textbox("Own-brand share and discount dependence"))
    brand.add("pl_dept", 20, 70, 620, 300, chart(
        "clusteredBarChart", column("Product", "department"), [measure("Private Label Share %")],
        "Own-brand share by department", sort_by=measure("Private Label Share %")))
    brand.add("promo_dept", 655, 70, 605, 300, chart(
        "clusteredBarChart", column("Product", "department"), [measure("Promo Sales Share %")],
        "Share of sales sold on loyalty discount", sort_by=measure("Promo Sales Share %")))
    brand.add("categories", 20, 385, 1240, 315, table(
        [column("Product", "department"), column("Product", "product_category"), measure("Net Sales"),
         measure("Private Label Share %"), measure("Discount Rate %"), measure("Households")],
        "Categories: size, own-brand share and discount rate", sort_by=measure("Net Sales")))

    return [overview, trends, customers, campaigns, brand]


def main() -> None:
    if DEFINITION.exists():
        for child in DEFINITION.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    write(REPORT_DIR / "definition.pbir", {
        "$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json", "version": "4.0",
        "datasetReference": {"byPath": {"path": "../Retail_Analytics.SemanticModel"}}})
    write(DEFINITION / "version.json", {
        "$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    write(DEFINITION / "report.json", {
        "$schema": f"{SCHEMA}/item/report/definition/report/1.0.0/schema.json",
        "themeCollection": {"baseTheme": {"name": THEME, "reportVersionAtImport": "5.55",
                                          "type": "SharedResources"}},
        "layoutOptimization": "None",
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources",
                              "items": [{"name": THEME, "path": f"BaseThemes/{THEME}.json", "type": "BaseTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True},
    })
    theme_target = REPORT_DIR / "StaticResources" / "SharedResources" / "BaseThemes" / f"{THEME}.json"
    if not theme_target.exists():
        theme_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(THEME_SOURCE, theme_target)
    pages = build_pages()
    for page in pages:
        page.save()
    write(DEFINITION / "pages" / "pages.json", {
        "$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p.name for p in pages], "activePageName": pages[0].name})
    print(f"Wrote {len(pages)} pages, {sum(len(p.visuals) for p in pages)} visuals to {DEFINITION}")


if __name__ == "__main__":
    main()
