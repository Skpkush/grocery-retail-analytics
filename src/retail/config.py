"""Paths and constants shared by every stage of the pipeline."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"  # downloaded source files, untouched
LANDING_DIR = DATA_DIR / "landing"  # source files converted to Parquet, untyped
WAREHOUSE_PATH = DATA_DIR / "warehouse.duckdb"
QUALITY_REPORT_PATH = DATA_DIR / "quality_report.json"
AUDIT_LOG_PATH = DATA_DIR / "audit_log.jsonl"
MODELS_DIR = PROJECT_ROOT / "sql" / "models"
ANALYSIS_DIR = PROJECT_ROOT / "sql" / "analysis"
REPORTS_DIR = PROJECT_ROOT / "reports"
POWERBI_DATA_DIR = PROJECT_ROOT / "powerbi" / "data"

SOURCE_BASE_URL = "https://github.com/bradleyboehmke/completejourney/raw/master/data"

# name -> source file. .rda files hold one named object; .rds files hold one frame.
SOURCE_FILES: dict[str, str] = {
    "transactions": "transactions.rds",
    "promotions": "promotions.rds",
    "products": "products.rda",
    "demographics": "demographics.rda",
    "campaigns": "campaigns.rda",
    "campaign_descriptions": "campaign_descriptions.rda",
    "coupons": "coupons.rda",
    "coupon_redemptions": "coupon_redemptions.rda",
}

# Tables small enough to load in CI without the two large files.
CORE_TABLES = ("products", "demographics", "campaigns", "campaign_descriptions",
               "coupons", "coupon_redemptions")

MAX_SQL_ROWS = 500

# Empty stand-ins for sources skipped with RETAIL_SKIP_TABLES (e.g. the 20.9M-row
# promotions file on a small CI runner). Keeps every downstream model valid.
EMPTY_SCHEMAS: dict[str, str] = {
    "promotions": "NULL::VARCHAR AS product_id, NULL::VARCHAR AS store_id, "
                  "NULL::VARCHAR AS display_location, NULL::VARCHAR AS mailer_location, "
                  "NULL::INTEGER AS week",
}


def skipped_tables() -> set[str]:
    raw = os.getenv("RETAIL_SKIP_TABLES", "")
    names = {name.strip() for name in raw.split(",") if name.strip()}
    unknown = names - set(EMPTY_SCHEMAS)
    if unknown:
        raise ValueError(f"Only {sorted(EMPTY_SCHEMAS)} can be skipped, not {sorted(unknown)}.")
    return names


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}
