"""Capture README screenshots of the running Streamlit app (dev tool).

    streamlit run app.py          # in another terminal, port 8501 by default
    python docs/images/capture_screenshots.py --port 8501

Uses Playwright with the locally installed Microsoft Edge (no browser download).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
PAGES = {"streamlit_overview": "", "streamlit_customers": "customers",
         "streamlit_campaigns": "campaigns", "streamlit_promotions": "promotions",
         "streamlit_quality": "quality", "streamlit_ask": "ask"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        for name, path in PAGES.items():
            page.goto(f"http://localhost:{args.port}/{path}")
            page.wait_for_selector("[data-testid='stMainBlockContainer'] h1", timeout=60_000)
            page.wait_for_load_state("networkidle")
            page.wait_for_function(  # Streamlit shows a "running" indicator until the script finishes
                "!document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=90_000)
            page.wait_for_timeout(2500)  # let Plotly finish drawing
            if path == "ask":
                page.get_by_label("Your question").fill("Are coupons incremental?")
                page.keyboard.press("Enter")
                page.wait_for_selector("text=How far this can be trusted", timeout=60_000)
                page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
            print("saved", name)
        browser.close()


if __name__ == "__main__":
    main()
