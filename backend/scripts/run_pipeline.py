#!/usr/bin/env python3
"""
ArcVault CLI Runner — processes all 5 sample inputs via Anthropic API directly.
No FastAPI or n8n required. Use this to generate data/outputs/processed_records.json.

Usage (from repo root):
    cp .env.example .env   # add ANTHROPIC_API_KEY
    pip install anthropic python-dotenv
    python backend/scripts/run_pipeline.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Config ────────────────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-6"
CONFIDENCE_ESCALATION_THRESHOLD = 0.70
ESCALATION_KEYWORDS = [
    "outage", "down for all users", "multiple users affected",
    "not loading", "stopped loading", "completely down",
]
BILLING_ESCALATION_THRESHOLD = 200

BASE_DIR = Path(__file__).parent.parent.parent  # backend/scripts/ → backend/ → repo root
INPUT_FILE = BASE_DIR / "data" / "sample_inputs.json"
OUTPUT_FILE = BASE_DIR / "data" / "outputs" / "processed_records.json"

ROUTING_TABLE = {
    "Bug Report": "Engineering",
    "Incident / Outage": "Engineering",
    "Feature Request": "Product",
    "Technical Question": "IT / Security",
    "Billing Issue": "Billing",
}

# ── Prompts ───────────────────────────────────────────────────────────────────

def classification_prompt(raw_message: str) -> str:
    return f"""You are a B2B SaaS support triage specialist for ArcVault. Classify the inbound message.

Return a JSON object with exactly these fields:
{{
  "category": "<one of: Bug Report | Feature Request | Billing Issue | Technical Question | Incident / Outage>",
  "priority": "<one of: Low | Medium | High>",
  "confidence_score": <float 0.0–1.0>
}}

Priority: High=service disruption/billing error/blocked access. Medium=degraded functionality. Low=inquiry.
Confidence: 0.9+=clear. 0.7-0.89=likely. 0.5-0.69=ambiguous. <0.5=insufficient.

Return ONLY the JSON. No markdown, no explanation.

Message:
{raw_message}"""


def enrichment_prompt(raw_message: str, category: str, priority: str) -> str:
    return f"""You are a support data analyst for ArcVault. Extract structured information from the message.

Classification: {category} | {priority}

Return JSON with:
{{
  "core_issue": "<one sentence summary>",
  "identifiers": {{ "<key>": "<value>" }},
  "urgency_signal": "<one sentence urgency assessment>"
}}

Only include identifiers present in the message. Possible keys:
account_id, invoice_number, error_code, affected_component, feature_requested,
integration_requested, incident_start, billed_amount, contracted_rate, discrepancy,
trigger_event, scope, use_case, context

Do not invent values. Return ONLY the JSON.

Message:
{raw_message}"""


def summary_prompt(record: dict) -> str:
    return f"""Write a 2–3 sentence internal handoff note for the ArcVault support team.
State the issue, include key identifiers, end with a recommended action. Professional tone, no filler.

Record:
- Category: {record['classification']['category']}
- Priority: {record['classification']['priority']}
- Core Issue: {record['enrichment']['core_issue']}
- Identifiers: {json.dumps(record['enrichment']['identifiers'])}
- Urgency: {record['enrichment']['urgency_signal']}
- Escalated: {record['routing']['escalation_flag']}
- Source: {record['source']}

Return ONLY the summary text."""


# ── LLM call ──────────────────────────────────────────────────────────────────

def call_llm(client: anthropic.Anthropic, prompt: str) -> dict | str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


# ── Escalation + Routing ──────────────────────────────────────────────────────

def check_escalation(raw_message: str, classification: dict, enrichment: dict) -> tuple[bool, str | None]:
    msg_lower = raw_message.lower()

    if classification["confidence_score"] < CONFIDENCE_ESCALATION_THRESHOLD:
        return True, f"Confidence {classification['confidence_score']:.0%} below {CONFIDENCE_ESCALATION_THRESHOLD:.0%} threshold"

    for kw in ESCALATION_KEYWORDS:
        if kw in msg_lower:
            return True, f"Escalation keyword matched: '{kw}'"

    identifiers = enrichment.get("identifiers", {})
    if "discrepancy" in identifiers:
        try:
            amount = float(identifiers["discrepancy"].replace("$", "").replace(",", "").strip())
            if amount > BILLING_ESCALATION_THRESHOLD:
                return True, f"Billing discrepancy ${amount:.0f} exceeds ${BILLING_ESCALATION_THRESHOLD} threshold"
        except ValueError:
            pass

    if classification["category"] == "Incident / Outage":
        return True, "Incident / Outage auto-escalates"

    return False, None


def route(classification: dict, escalation_flag: bool, escalation_reason: str | None) -> dict:
    if escalation_flag:
        return {
            "destination_queue": "Escalation",
            "routing_reason": escalation_reason or "Escalation condition met",
            "escalation_flag": True,
            "escalation_reason": escalation_reason,
        }
    category = classification["category"]
    queue = ROUTING_TABLE.get(category, "Escalation")
    return {
        "destination_queue": queue,
        "routing_reason": f"{category} routes to {queue} queue",
        "escalation_flag": False,
        "escalation_reason": None,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def process_message(client: anthropic.Anthropic, msg: dict) -> dict:
    print(f"  {msg['id']} ({msg['source']})...")

    classification = call_llm(client, classification_prompt(msg["raw_message"]))
    print(f"    → {classification['category']} | {classification['priority']} | {classification['confidence_score']:.0%}")

    enrichment = call_llm(client, enrichment_prompt(
        msg["raw_message"], classification["category"], classification["priority"]
    ))

    escalation_flag, escalation_reason = check_escalation(msg["raw_message"], classification, enrichment)
    routing = route(classification, escalation_flag, escalation_reason)
    print(f"    → {routing['destination_queue']} | escalated={escalation_flag}")

    record = {
        "id": msg["id"],
        "source": msg["source"],
        "timestamp": msg.get("timestamp", datetime.utcnow().isoformat() + "Z"),
        "raw_message": msg["raw_message"],
        "classification": classification,
        "enrichment": enrichment,
        "routing": routing,
    }

    summary = call_llm(client, summary_prompt(record))
    record["summary"] = summary if isinstance(summary, str) else str(summary)
    return record


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    with open(INPUT_FILE) as f:
        messages = json.load(f)

    print(f"Processing {len(messages)} messages with {MODEL}...\n")
    results = [process_message(client, msg) for msg in messages]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    escalated = sum(1 for r in results if r["routing"]["escalation_flag"])
    print(f"\n✓ Done → {OUTPUT_FILE}")
    print(f"  {len(results)} records | {escalated} escalated | {len(results) - escalated} routed")


if __name__ == "__main__":
    main()
