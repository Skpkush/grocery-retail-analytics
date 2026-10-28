from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from retail.config import WAREHOUSE_PATH  # noqa: E402

requires_warehouse = pytest.mark.skipif(
    not WAREHOUSE_PATH.exists(), reason="Run `python -m retail.pipeline` first.")
