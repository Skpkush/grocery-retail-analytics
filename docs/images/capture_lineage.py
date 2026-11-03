"""Save a screenshot of the dbt lineage graph to docs/images/dbt_lineage.png.

    dbt docs generate
    dbt docs serve --port 8580 --no-browser      # in another terminal
    python docs/images/capture_lineage.py         # needs `pip install playwright`

Uses the installed Microsoft Edge (or Chrome with --browser chrome), so no
browser download is needed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "dbt_lineage.png"
# Every model and source upstream of the two exposures; tests are hidden.
SELECT = "+exposure:power_bi_retail_report +exposure:streamlit_app"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8580")
    parser.add_argument("--browser", default="msedge", choices=["msedge", "chrome"])
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.browser)
        page = browser.new_page(viewport={"width": 2200, "height": 1250}, device_scale_factor=1)
        page.goto(f"{args.url}/#!/overview?g_v=1", wait_until="domcontentloaded")
        include = page.locator("input[ng-model='selectorService.selection.dirty.include']")
        include.wait_for()
        include.fill(SELECT)
        include.press("Enter")
        page.get_by_text("Update Graph").click()
        page.wait_for_timeout(4000)  # cytoscape layout animation
        page.locator(".dbt-graph, #cy, .graph-container").first.screenshot(path=str(OUT))
        browser.close()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
