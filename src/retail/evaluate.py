"""Score the copilot on a golden question set (routing, data, citations, latency).

    python -m retail.evaluate             # scorecard -> reports/eval_results.md
    python -m retail.evaluate --min 0.9   # exit 1 below a 90% pass rate (CI gate)
"""

from __future__ import annotations

import argparse
import json
import os
import statistics

from retail.config import PROJECT_ROOT, REPORTS_DIR

GOLDEN_PATH = PROJECT_ROOT / "evals" / "golden_questions.json"
RESULTS_PATH = REPORTS_DIR / "eval_results.md"


def evaluate() -> tuple[list[dict], dict]:
    os.environ["RETAIL_OFFLINE"] = "1"  # deterministic scoring
    from retail.copilot import ask

    results = []
    for case in json.loads(GOLDEN_PATH.read_text(encoding="utf-8")):
        r = ask(case["question"])
        fails = []
        if r.route != case["expected_route"]:
            fails.append(f"route={r.route}, expected {case['expected_route']}")
        if "expected_rows" in case and len(r.rows) != case["expected_rows"]:
            fails.append(f"rows={len(r.rows)}, expected {case['expected_rows']}")
        fails += [f"missing column {c}" for c in case.get("expected_columns", []) if c not in r.columns]
        fails += [f"missing source {s}" for s in case.get("expected_sources", [])
                  if not any(s in src for src in r.sources)]
        fails += [f"answer missing '{p}'" for p in case.get("must_contain", []) if p not in r.answer]
        if "**Sources:**" not in r.answer:
            fails.append("no Sources section")
        if r.error:
            fails.append(f"error: {r.error}")
        results.append({"id": case["id"], "passed": not fails, "route_ok": r.route == case["expected_route"],
                        "latency_ms": r.latency_ms, "failures": fails})
    n = len(results)
    scores = {
        "cases": n,
        "pass_rate": sum(r["passed"] for r in results) / n,
        "route_accuracy": sum(r["route_ok"] for r in results) / n,
        "p50_latency_ms": statistics.median(r["latency_ms"] for r in results),
    }
    return results, scores


def render(results: list[dict], scores: dict) -> str:
    lines = ["# Copilot evaluation scorecard", "", "| Metric | Value |", "| --- | --- |",
             f"| Cases | {scores['cases']} |", f"| Pass rate | {scores['pass_rate']:.0%} |",
             f"| Routing accuracy | {scores['route_accuracy']:.0%} |",
             f"| p50 latency | {scores['p50_latency_ms']:.0f} ms |", "",
             "| Case | Result | Latency | Notes |", "| --- | --- | --- | --- |"]
    lines += [f"| {r['id']} | {'PASS' if r['passed'] else 'FAIL'} | {r['latency_ms']} ms | "
              f"{'; '.join(r['failures']) or '-'} |" for r in results]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min", type=float, default=0.0)
    args = parser.parse_args()
    results, scores = evaluate()
    text = render(results, scores)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(text, encoding="utf-8")
    print(text)
    if scores["pass_rate"] < args.min:
        raise SystemExit(f"Pass rate {scores['pass_rate']:.0%} is below {args.min:.0%}.")


if __name__ == "__main__":
    main()
