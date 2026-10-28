"""Ask-the-data copilot: governed SQL + cited documentation, with an audit trail.

Routing:
  sql   - a metric question. Answered from the SQL analysis library when a
          library query matches, otherwise from a template built on the metric
          layer, or (with OPENAI_API_KEY) LLM-written SQL. All SQL passes the guard.
  docs  - a definition/method question. Answered from docs/ and the insights
          report with BM25 retrieval and filename citations.
  both  - a "why / what should we do" question: data plus methodology.

Without an API key everything runs offline and deterministically; that is what
CI and the evaluation harness use.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from retail.analytics import get_analysis
from retail.config import AUDIT_LOG_PATH, PROJECT_ROOT
from retail.metrics import metric_glossary, select_metrics
from retail.sql_guard import execute_readonly_query, get_schema_description, validate_sql

DOC_PATHS = [PROJECT_ROOT / "docs" / "data_dictionary.md", PROJECT_ROOT / "docs" / "methodology.md",
             PROJECT_ROOT / "reports" / "insights.md"]

# keyword pattern -> analysis library key (first match wins, so order matters)
LIBRARY_ROUTES: list[tuple[str, str]] = [
    (r"coupon", "coupon_incrementality"),
    (r"campaign", "campaign_reach"),
    (r"display|mailer|promotion|promoted", "promotion_lift"),
    (r"private label|own[- ]brand|store brand", "private_label_gap"),
    (r"deal|discount dependen|discount[- ]sensitive", "discount_dependency"),
    (r"rfm|segment|at[- ]risk|champion|lapsed|win[- ]back", "rfm_segments"),
    (r"concentrat|pareto|top 10%|top 20%|decile", "customer_concentration"),
    (r"income|demographic|household size|kids|age group", "demographic_spend"),
    (r"bought together|affinity|market basket|cross[- ]sell", "market_basket"),
    (r"day of (the )?week|what time|hour|daypart|when do", "shopping_patterns"),
    (r"department", "department_performance"),
    (r"week|weekly|trend|holiday", "weekly_trend"),
    (r"quarter|q[1-4]\b|kpi|overall|headline", "kpi_by_quarter"),
]

QUARTERS = {"q1": 1, "q2": 2, "q3": 3, "q4": 4}
STOP = set("the a an and or of to in on for by with what which who how is are was were did do does "
           "our we me show tell give list top most best highest last this that from per".split())


@dataclass
class CopilotResult:
    answer: str
    route: str
    sql: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    mode: str = "offline"
    latency_ms: int = 0
    error: str | None = None


# --- retrieval ----------------------------------------------------------------

def _stem(token: str) -> str:
    """Light stemmer: plural/ing/ed endings, then a 7-character prefix."""
    for suffix in ("ies", "ing", "ed", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            token = token[: -len(suffix)] + ("y" if suffix == "ies" else "")
            break
    return token[:7]


def _tokens(text: str) -> list[str]:
    return [_stem(t) for t in re.findall(r"[a-z0-9%]+", text.lower()) if t not in STOP and len(t) > 1]


@lru_cache(maxsize=1)
def _chunks() -> list[tuple[str, str]]:
    chunks = []
    for path in DOC_PATHS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if path.name == "insights.md":  # only the narrative findings, not the tables
            text = text.split("## ", 2)[1] if "## " in text else text
        for block in re.split(r"\n(?=#{1,3} )|\n\s*\n", text):
            block = block.strip()
            if len(block) > 60 and not block.startswith("|"):
                chunks.append((path.name, block))
    return chunks


def search_docs(question: str, k: int = 3) -> list[tuple[str, str, float]]:
    """BM25 over documentation chunks."""
    chunks = _chunks()
    docs = [_tokens(c[1]) for c in chunks]
    if not docs:
        return []
    avg = sum(map(len, docs)) / len(docs)
    df = Counter(t for d in docs for t in set(d))
    query = _tokens(question)
    scored = []
    for (source, text), toks in zip(chunks, docs, strict=True):
        tf = Counter(toks)
        score = 0.0
        for t in query:
            if t not in tf:
                continue
            idf = math.log(1 + (len(docs) - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * len(toks) / avg))
        if score > 0:
            scored.append((source, text, score))
    return sorted(scored, key=lambda x: x[2], reverse=True)[:k]


# --- routing and SQL planning -------------------------------------------------

def route(question: str) -> str:
    q = question.lower().strip()
    if re.match(r"^(hi|hello|hey|thanks|thank you)\b", q):
        return "none"
    definitional = re.search(r"\b(what (is|does|are) (a |an |the )?(\w+ )?(mean|definition)|define|"
                             r"definition|how (is|are|do you) .* (calculated|measured|defined)|"
                             r"methodology|why (is|are) .* excluded|limitation|caveat|"
                             r"time ?zone|what does .* mean)\b", q)
    causal = re.search(r"\b(why|should we|recommend|what should|worth it|incremental|roi|"
                       r"effective|impact|lift)\b|\bwork(ing|s)?\s*\??$", q)
    metric = re.search(r"\b(sales|revenue|spend|baskets?|households?|units|share|top|rank|"
                       r"lift|rate|how (much|many)|compare|trend|growth|segment|coupons?|"
                       r"campaigns?|promotions?|department|categor\w*|products?|"
                       r"private label|own[- ]brand|opportunit\w*|rfm|at[- ]risk|"
                       r"bought together|affinity)\b", q)
    if definitional and not re.search(r"\b(top|how much|how many|rank)\b", q):
        return "docs"
    if causal and metric:
        return "both"
    if metric:
        return "sql"
    return "docs"


def _department(question: str) -> str | None:
    q = question.upper()
    for dept in ("GROCERY", "DRUG GM", "PRODUCE", "MEAT-PCKGD", "MEAT", "DELI", "PASTRY",
                 "NUTRITION", "SEAFOOD", "FLORAL", "COSMETICS", "SPIRITS"):
        if re.search(rf"\b{re.escape(dept)}\b", q):
            return dept
    return None


def plan_sql(question: str) -> tuple[str, str]:
    """Return (sql, source label) for a metric question, offline."""
    q = question.lower()
    top = re.search(r"\btop\s+(\d+)\b", q)
    limit = min(int(top.group(1)), 50) if top else 10
    quarter = next((n for k, n in QUARTERS.items() if re.search(rf"\b{k}\b", q)), None)
    dept = _department(question)
    filters = ["s.is_merch"]
    if quarter:
        filters.append(f"d.quarter_number = {quarter}")
    if dept:
        filters.append(f"p.department = '{dept}'")
    where = " AND ".join(filters)

    if re.search(r"bought together|affinity|market basket|cross[- ]sell", q):
        analysis = get_analysis("market_basket")
        return analysis.sql, f"SQL library: {analysis.path.name}"
    if re.search(r"\b(top|best|highest|biggest)\b.*\b(products?|items?)\b", q):
        # The source has no product names; product_type is the most specific label.
        sql = (f"SELECT p.product_id, p.department, p.product_category, p.product_type, p.brand,\n  "
               f"{select_metrics('net_sales', 'households', 'units')}\n"
               "FROM fct_sales s JOIN dim_product p USING (product_id)\n"
               f"JOIN dim_date d ON d.date_key = s.business_date\nWHERE {where}\n"
               f"GROUP BY ALL ORDER BY net_sales DESC LIMIT {limit}")
        return sql, "SQL: metric layer (top products)"
    if re.search(r"\b(top|best|highest|biggest)\b.*\bcategor", q) or (
            re.search(r"\bcategor", q) and not re.search(r"private|own", q)):
        sql = (f"SELECT p.department, p.product_category,\n  "
               f"{select_metrics('net_sales', 'households', 'discount_rate_pct', 'private_label_share_pct')}\n"
               "FROM fct_sales s JOIN dim_product p USING (product_id)\n"
               f"JOIN dim_date d ON d.date_key = s.business_date\nWHERE {where}\n"
               f"GROUP BY ALL ORDER BY net_sales DESC LIMIT {limit}")
        return sql, "SQL: metric layer (categories)"
    if (quarter or dept) and not re.search(r"campaign|coupon|promotion|segment", q):
        sql = (f"SELECT\n  {select_metrics('net_sales', 'baskets', 'households', 'avg_basket_value', 'discount_rate_pct', 'private_label_share_pct')}\n"
               "FROM fct_sales s JOIN dim_product p USING (product_id)\n"
               f"JOIN dim_date d ON d.date_key = s.business_date\nWHERE {where}")
        return sql, "SQL: metric layer (filtered KPIs)"
    for pattern, key in LIBRARY_ROUTES:
        if re.search(pattern, q):
            analysis = get_analysis(key)
            return analysis.sql, f"SQL library: {analysis.path.name}"
    analysis = get_analysis("kpi_by_quarter")
    return analysis.sql, f"SQL library: {analysis.path.name}"


# --- optional LLM path ----------------------------------------------------------

def _llm_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and os.getenv("RETAIL_OFFLINE", "") not in {"1", "true"}


def _chat(system: str, user: str) -> str:
    from openai import OpenAI  # optional dependency

    client = OpenAI()
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return response.choices[0].message.content or ""


def _llm_sql(question: str, error: str | None = None) -> str:
    system = (
        "Write exactly one DuckDB SELECT query for the question. Use only these tables:\n"
        f"{get_schema_description()}\n\nGoverned metrics (use these expressions exactly):\n"
        f"{metric_glossary()}\nAliases: s = fct_sales, p = dim_product, d = dim_date "
        "(join d.date_key = s.business_date). Return SQL only, no markdown."
    )
    user = question + (f"\n\nThe previous query failed: {error}. Fix it." if error else "")
    return _chat(system, user)


# --- answer composition -------------------------------------------------------

def _takeaway(columns: list[str], rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "The query returned no rows."
    numeric = [c for c in columns if all(isinstance(r.get(c), (int, float)) or r.get(c) is None for r in rows)]
    labels = [c for c in columns if c not in numeric]
    preferred = [c for c in ("net_sales", "sales_lift_pct", "habitual_pct", "lift",
                             "sales_share_pct", "household_redemption_rate_pct") if c in numeric]
    metric = preferred[0] if preferred else (numeric[0] if numeric else None)
    if metric is None:
        return f"The query returned {len(rows)} rows."
    if len(rows) == 1 or not labels:
        parts = [f"{c.replace('_', ' ')} = {rows[0][c]:,.2f}" for c in numeric[:4] if rows[0][c] is not None]
        return "; ".join(parts) + "."
    lead = max(rows, key=lambda r: (r.get(metric) is not None, r.get(metric) or 0))
    label = " / ".join(str(lead[c]) for c in labels[:2])
    return f"{label} leads on {metric.replace('_', ' ')} ({lead[metric]:,.2f})."


def _audit(result: CopilotResult, question: str) -> None:
    entry = {"ts": datetime.now(UTC).isoformat(timespec="seconds"), "question": question,
             "route": result.route, "mode": result.mode, "sql": result.sql,
             "rows": len(result.rows), "sources": result.sources,
             "latency_ms": result.latency_ms, "error": result.error}
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, default=str) + "\n")
    except OSError:
        pass  # logging must never break answering


def ask(question: str) -> CopilotResult:
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")
    started = time.perf_counter()
    question = question.strip()
    result = CopilotResult(answer="", route=route(question),
                           mode="openai" if _llm_enabled() else "offline")
    parts: list[str] = []

    if result.route == "none":
        parts.append("Ask me about sales, departments, households, campaigns, coupons, "
                     "promotions or how a metric is defined.")

    if result.route in {"sql", "both"}:
        try:
            if _llm_enabled():
                sql, label = _llm_sql(question), "SQL: generated, governed"
                try:
                    validate_sql(sql)
                    data = execute_readonly_query(sql, max_rows=200)
                except Exception as exc:  # one self-correction attempt
                    sql = _llm_sql(question, error=str(exc))
                    data = execute_readonly_query(sql, max_rows=200)
            else:
                sql, label = plan_sql(question)
                data = execute_readonly_query(sql, max_rows=200)
            result.sql, result.columns, result.rows = data.sql, data.columns, data.rows
            result.sources.append(label)
            parts += ["**Answer:** " + _takeaway(data.columns, data.rows), "", data.to_markdown(max_rows=15)]
        except Exception as exc:
            result.error = str(exc)
            parts.append(f"I could not run the warehouse query: {exc}")

    if result.route in {"docs", "both"}:
        hits = search_docs(question, k=2 if result.route == "both" else 3)
        if hits:
            parts += ["", "**From the documentation:**" if result.route == "both" else "**Answer:**"]
            for source, text, _ in hits:
                excerpt = text.strip()
                if len(excerpt) > 1200:  # cut at a sentence boundary
                    excerpt = excerpt[:1200].rsplit(". ", 1)[0] + "."
                quoted = "\n".join(f"> {line}" for line in excerpt.splitlines())
                parts.append(f"{quoted}\n>\n> Source: _{source}_\n")
                if source not in result.sources:
                    result.sources.append(source)
        elif result.route == "docs":
            parts.append("I could not find this in the documentation.")

    sources = result.sources or ["No source"]
    result.answer = "\n".join(parts).strip() + "\n\n**Sources:**\n" + "\n".join(f"- {s}" for s in sources)
    result.latency_ms = round(1000 * (time.perf_counter() - started))
    _audit(result, question)
    return result
