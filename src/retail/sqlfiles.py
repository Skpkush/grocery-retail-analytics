"""Read the dbt analyses as plain SQL that runs against the warehouse.

The files in ``analyses/`` use ``{{ ref('model') }}`` so dbt tracks their
lineage. Every model lives in the warehouse's default schema under its own
name, so ``ref('fct_sales')`` resolves to ``fct_sales`` here.
"""

from __future__ import annotations

import re
from pathlib import Path

_REF = re.compile(r"\{\{\s*ref\(\s*['\"](\w+)['\"]\s*\)\s*\}\}")


def render(sql: str) -> str:
    if "{{" in _REF.sub("", sql) or "{%" in sql:
        raise ValueError("Only {{ ref('model') }} is supported in analyses.")
    return _REF.sub(r"\1", sql)


def read(path: Path) -> str:
    return render(path.read_text(encoding="utf-8"))
