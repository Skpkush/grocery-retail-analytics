"""Read the copilot audit trail (written by ``retail.copilot.ask``)."""

from __future__ import annotations

import json
from typing import Any

from retail.config import AUDIT_LOG_PATH


def read_recent(limit: int = 50) -> list[dict[str, Any]]:
    if not AUDIT_LOG_PATH.exists():
        return []
    events = []
    for line in reversed(AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines()[-limit:]):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events
