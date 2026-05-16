#!/usr/bin/env python3
"""
Validates processed_records.json against the required output schema.
Run after the pipeline to confirm all records pass before submission.

Usage (from repo root):
    python backend/scripts/validate_outputs.py
"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent  # backend/scripts/ → backend/ → repo root
OUTPUT_FILE = BASE_DIR / "data" / "outputs" / "processed_records.json"

VALID_CATEGORIES = {"Bug Report", "Feature Request", "Billing Issue", "Technical Question", "Incident / Outage"}
VALID_PRIORITIES = {"Low", "Medium", "High"}
VALID_QUEUES = {"Engineering", "Billing", "Product", "IT / Security", "Escalation"}

errors: list[str] = []
warnings: list[str] = []


def check(condition: bool, msg: str, record_id: str, fatal: bool = True) -> None:
    if not condition:
        (errors if fatal else warnings).append(f"[{record_id}] {msg}")


def validate_record(r: dict, idx: int) -> None:
    rid = r.get("id", f"record[{idx}]")

    for field in ["id", "source", "timestamp", "raw_message", "classification", "enrichment", "routing", "summary"]:
        check(field in r, f"Missing field: '{field}'", rid)

    c = r.get("classification", {})
    check(c.get("category") in VALID_CATEGORIES, f"Invalid category: '{c.get('category')}'", rid)
    check(c.get("priority") in VALID_PRIORITIES, f"Invalid priority: '{c.get('priority')}'", rid)
    score = c.get("confidence_score")
    check(isinstance(score, (int, float)) and 0.0 <= score <= 1.0, f"Invalid confidence_score: {score!r}", rid)

    e = r.get("enrichment", {})
    check("core_issue" in e and isinstance(e.get("core_issue"), str) and len(e["core_issue"]) > 0, "Missing core_issue", rid)
    check("identifiers" in e and isinstance(e.get("identifiers"), dict), "Missing/invalid identifiers", rid)
    check("urgency_signal" in e and isinstance(e.get("urgency_signal"), str), "Missing urgency_signal", rid)

    ro = r.get("routing", {})
    check(ro.get("destination_queue") in VALID_QUEUES, f"Invalid destination_queue: '{ro.get('destination_queue')}'", rid)
    check(isinstance(ro.get("escalation_flag"), bool), f"escalation_flag must be bool, got: {ro.get('escalation_flag')!r}", rid)
    if ro.get("escalation_flag"):
        check(ro.get("escalation_reason"), "escalation_flag=True but escalation_reason is missing", rid)

    summary = r.get("summary", "")
    check(isinstance(summary, str) and len(summary) > 20, f"Summary too short: '{summary[:40]}'", rid)
    check(len(summary.split(".")) >= 2, "Summary should be 2–3 sentences", rid, fatal=False)

    if c.get("category") == "Incident / Outage":
        check(ro.get("escalation_flag") is True, "Incident/Outage should always be escalated", rid, fatal=False)
    if isinstance(score, float) and score < 0.70:
        check(ro.get("escalation_flag") is True, f"Confidence {score:.0%} < 70% but not escalated", rid)


def main() -> None:
    if not OUTPUT_FILE.exists():
        print(f"ERROR: {OUTPUT_FILE} not found.")
        print("Run: python backend/scripts/run_pipeline.py")
        sys.exit(1)

    with open(OUTPUT_FILE) as f:
        records = json.load(f)

    print(f"Validating {len(records)} records in {OUTPUT_FILE}...\n")
    for i, r in enumerate(records):
        validate_record(r, i)

    print("── Record Summary ──────────────────────────────────")
    for r in records:
        rid = r.get("id", "?")
        cat = r.get("classification", {}).get("category", "?")
        queue = r.get("routing", {}).get("destination_queue", "?")
        score = r.get("classification", {}).get("confidence_score", 0)
        flag = " ⚑ ESCALATED" if r.get("routing", {}).get("escalation_flag") else ""
        print(f"  {rid}: {cat} → {queue} ({score:.0%}){flag}")

    escalated = sum(1 for r in records if r.get("routing", {}).get("escalation_flag"))
    print(f"\n── Stats ───────────────────────────────────────────")
    print(f"  Total: {len(records)} | Escalated: {escalated} | Standard: {len(records) - escalated}")

    if errors:
        print(f"\n── Errors ({len(errors)}) ──────────────────────────────")
        for e in errors:
            print(f"  ✗ {e}")
    if warnings:
        print(f"\n── Warnings ({len(warnings)}) ────────────────────────────")
        for w in warnings:
            print(f"  ⚠ {w}")

    if not errors:
        print("\n✓ All records valid — ready to submit.")
    else:
        print(f"\n✗ Validation failed with {len(errors)} error(s).")
        sys.exit(1)


if __name__ == "__main__":
    main()
