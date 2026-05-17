#!/usr/bin/env python3
"""
Validates processed_records.json against the required output schema.
Matches the flat 15-field schema produced by both the n8n workflow and run_pipeline.py.

Usage (from repo root):
    python backend/scripts/validate_outputs.py
"""

import json
import sys
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent.parent  # repo root
OUTPUT_FILE = BASE_DIR / "data" / "outputs" / "processed_records.json"

VALID_CATEGORIES = {"Bug Report", "Feature Request", "Billing Issue", "Technical Question", "Incident / Outage"}
VALID_PRIORITIES = {"Low", "Medium", "High"}
VALID_QUEUES     = {"Engineering", "Billing", "Product", "IT / Security", "Escalation"}

# All required top-level fields in the flat output schema
REQUIRED_FIELDS = [
    "id", "source", "timestamp", "raw_message",
    "category", "priority", "confidence_score",
    "core_issue", "identifiers", "urgency_signal",
    "destination_queue", "routing_reason",
    "escalation_flag", "escalation_reason",
    "summary",
]

errors:   list[str] = []
warnings: list[str] = []


def fail(msg: str, rid: str) -> None:
    errors.append(f"[{rid}] {msg}")


def warn(msg: str, rid: str) -> None:
    warnings.append(f"[{rid}] {msg}")


def validate_record(r: dict, idx: int) -> None:
    rid = r.get("id", f"record[{idx}]")

    # ── Required fields present ───────────────────────────────────────────────
    for field in REQUIRED_FIELDS:
        if field not in r:
            fail(f"Missing field: '{field}'", rid)

    # ── Classification fields ─────────────────────────────────────────────────
    if r.get("category") not in VALID_CATEGORIES:
        fail(f"Invalid category: {r.get('category')!r}", rid)

    if r.get("priority") not in VALID_PRIORITIES:
        fail(f"Invalid priority: {r.get('priority')!r}", rid)

    score = r.get("confidence_score")
    if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
        fail(f"confidence_score must be float 0.0–1.0, got: {score!r}", rid)

    # ── Enrichment fields ─────────────────────────────────────────────────────
    if not isinstance(r.get("core_issue"), str) or not r.get("core_issue"):
        fail("core_issue must be a non-empty string", rid)

    if not isinstance(r.get("identifiers"), dict):
        fail("identifiers must be a JSON object", rid)

    if not isinstance(r.get("urgency_signal"), str) or not r.get("urgency_signal"):
        fail("urgency_signal must be a non-empty string", rid)

    # ── Routing fields ────────────────────────────────────────────────────────
    if r.get("destination_queue") not in VALID_QUEUES:
        fail(f"Invalid destination_queue: {r.get('destination_queue')!r}", rid)

    if not isinstance(r.get("escalation_flag"), bool):
        fail(f"escalation_flag must be boolean, got: {r.get('escalation_flag')!r}", rid)

    if r.get("escalation_flag") and not r.get("escalation_reason"):
        fail("escalation_flag is true but escalation_reason is missing", rid)

    if not r.get("escalation_flag") and r.get("destination_queue") == "Escalation":
        fail("destination_queue is Escalation but escalation_flag is false", rid)

    # ── Summary ───────────────────────────────────────────────────────────────
    summary = r.get("summary", "")
    if not isinstance(summary, str) or len(summary) < 20:
        fail(f"summary too short or missing: {summary!r}", rid)
    elif len(summary.split(".")) < 2:
        warn("summary should be 2–3 sentences", rid)

    # ── Business logic checks ─────────────────────────────────────────────────
    if r.get("category") == "Incident / Outage" and not r.get("escalation_flag"):
        warn("Incident/Outage should always be escalated", rid)

    if isinstance(score, float) and score < 0.70 and not r.get("escalation_flag"):
        fail(f"confidence_score {score:.0%} < 70% but escalation_flag is false", rid)


def main() -> None:
    if not OUTPUT_FILE.exists():
        print(f"ERROR: {OUTPUT_FILE} not found.")
        print("Run:   python backend/scripts/run_pipeline.py")
        sys.exit(1)

    with open(OUTPUT_FILE) as f:
        records = json.load(f)

    if not isinstance(records, list) or len(records) == 0:
        print("ERROR: output file is empty or not a JSON array.")
        sys.exit(1)

    print(f"Validating {len(records)} records in {OUTPUT_FILE}...\n")
    for i, r in enumerate(records):
        validate_record(r, i)

    # ── Summary table ─────────────────────────────────────────────────────────
    print("── Records ─────────────────────────────────────────────────────────")
    for r in records:
        rid   = r.get("id", "?")
        cat   = r.get("category", "?")
        queue = r.get("destination_queue", "?")
        score = r.get("confidence_score", 0)
        flag  = " ⚑ ESCALATED" if r.get("escalation_flag") else ""
        reason = f" ({r['escalation_reason']})" if r.get("escalation_reason") else ""
        print(f"  {rid}: {cat} → {queue} ({score:.0%}){flag}{reason}")

    escalated = sum(1 for r in records if r.get("escalation_flag"))
    print(f"\n── Stats ───────────────────────────────────────────────────────────")
    print(f"  Total: {len(records)} | Escalated: {escalated} | Standard: {len(records) - escalated}")

    if errors:
        print(f"\n── Errors ({len(errors)}) ──────────────────────────────────────────────")
        for e in errors:
            print(f"  ✗ {e}")
    if warnings:
        print(f"\n── Warnings ({len(warnings)}) ────────────────────────────────────────────")
        for w in warnings:
            print(f"  ⚠ {w}")

    if not errors:
        print("\n✓ All records valid — ready to submit.")
    else:
        print(f"\n✗ Validation failed — {len(errors)} error(s) must be fixed before submission.")
        sys.exit(1)


if __name__ == "__main__":
    main()
