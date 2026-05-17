#!/usr/bin/env python3
"""
ArcVault CLI Runner — processes all 5 sample inputs via Groq API directly.
Matches the n8n workflow exactly: same model, same prompts, same output schema.
No FastAPI or n8n required. Use this to generate data/outputs/processed_records.json.

Usage (from repo root):
    cp backend/.env.example .env   # add GROQ_API_KEY
    pip install openai python-dotenv
    python backend/scripts/run_pipeline.py
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Run: pip install openai")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Config ────────────────────────────────────────────────────────────────────

MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

CONFIDENCE_THRESHOLD = 0.70
BILLING_THRESHOLD = 200
ESCALATION_KEYWORDS = [
    "outage",
    "down for all users",
    "multiple users affected",
    "stopped loading",
    "completely down",
]

ROUTING_TABLE = {
    "Bug Report":         "Engineering",
    "Incident / Outage":  "Engineering",
    "Feature Request":    "Product",
    "Technical Question": "IT / Security",
    "Billing Issue":      "Billing",
}

VALID_CATEGORIES = {"Bug Report", "Feature Request", "Billing Issue", "Technical Question", "Incident / Outage"}
VALID_PRIORITIES = {"Low", "Medium", "High"}

BASE_DIR   = Path(__file__).parent.parent.parent  # repo root
INPUT_FILE = BASE_DIR / "data" / "sample_inputs.json"
OUTPUT_FILE = BASE_DIR / "data" / "outputs" / "processed_records.json"

# ── LLM helpers ───────────────────────────────────────────────────────────────

def call_json(client: OpenAI, system: str, user: str) -> dict:
    """Call Groq with response_format: json_object — guaranteed valid JSON back."""
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return json.loads(response.choices[0].message.content)


def call_text(client: OpenAI, system: str, user: str) -> str:
    """Call Groq for plain text output (summary step)."""
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=256,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return response.choices[0].message.content.strip()


# ── Prompts ───────────────────────────────────────────────────────────────────

CLASSIFICATION_SYSTEM = """You are a B2B SaaS support triage specialist for ArcVault. You always respond with valid JSON only — no markdown, no explanation.

Classify the inbound customer message with exactly these fields:
{
  "category": "<Bug Report | Feature Request | Billing Issue | Technical Question | Incident / Outage>",
  "priority": "<Low | Medium | High>",
  "confidence_score": <float 0.0-1.0>
}

Priority rules:
- High: service disruption, blocked access, billing errors, security issues
- Medium: degraded functionality, feature requests with clear business impact
- Low: general inquiries, pre-sales, minor feedback

Confidence score bands:
- 0.90-1.0: clearly one category, no ambiguity
- 0.70-0.89: likely correct, minor signals point elsewhere
- 0.50-0.69: genuinely ambiguous between two categories
- below 0.50: insufficient information"""

ENRICHMENT_SYSTEM = """You are a support data analyst for ArcVault. You always respond with valid JSON only — no markdown, no explanation.

Given a customer message and its classification, extract structured information using this exact schema:
{
  "core_issue": "<one sentence: what the customer's actual problem or request is>",
  "identifiers": {
    "<key>": "<value>"
  },
  "urgency_signal": "<one sentence: why this is or is not urgent based on message content>"
}

For identifiers, only include keys that have a value present in the message. Valid keys:
account_id, invoice_number, error_code, affected_component, feature_requested,
integration_requested, incident_start, billed_amount, contracted_rate, discrepancy,
trigger_event, scope, use_case, context

Do not invent or infer values not stated in the message. If no identifiers are present, return an empty object {}."""

SUMMARY_SYSTEM = """You write internal handoff notes for the ArcVault support team. Write exactly 2-3 sentences. Professional, direct tone — no filler phrases like 'I hope this helps' or 'please let me know'. State the issue, include key identifiers, end with a concrete recommended action for the receiving team. Return only the summary text — no labels, no JSON."""


# ── Escalation + Routing ──────────────────────────────────────────────────────

def check_escalation(raw_message: str, category: str, confidence: float, identifiers: dict) -> tuple[bool, str | None]:
    msg_lower = raw_message.lower()

    if confidence < CONFIDENCE_THRESHOLD:
        return True, f"Low confidence ({confidence:.0%}) — below {CONFIDENCE_THRESHOLD:.0%} threshold"

    for kw in ESCALATION_KEYWORDS:
        if kw in msg_lower:
            return True, f"Escalation keyword matched: \"{kw}\""

    if "discrepancy" in identifiers:
        try:
            amount = float(str(identifiers["discrepancy"]).replace("$", "").replace(",", "").strip())
            if amount > BILLING_THRESHOLD:
                return True, f"Billing discrepancy ${amount:.0f} exceeds ${BILLING_THRESHOLD} threshold"
        except ValueError:
            pass

    if category == "Incident / Outage":
        return True, "Incident/Outage auto-escalates regardless of confidence"

    return False, None


# ── Pipeline ──────────────────────────────────────────────────────────────────

def process_message(client: OpenAI, msg: dict) -> dict:
    print(f"  {msg['id']} ({msg['source']})...")

    # Step 1: Ingestion
    record_id = msg.get("id", f"msg_{int(datetime.now(timezone.utc).timestamp() * 1000)}")
    timestamp = msg.get("timestamp", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    # Step 2: Classification — json_object enforced at API level
    classification = call_json(
        client,
        CLASSIFICATION_SYSTEM,
        msg["raw_message"],
    )
    category   = classification["category"].strip()
    priority   = classification["priority"].strip()
    confidence = float(classification["confidence_score"])

    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category: {category!r}")
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority: {priority!r}")

    print(f"    → {category} | {priority} | {confidence:.0%}")

    # Step 3: Enrichment — json_object enforced at API level
    enrichment = call_json(
        client,
        ENRICHMENT_SYSTEM,
        f"Category: {category}\nPriority: {priority}\n\nMessage:\n{msg['raw_message']}",
    )
    if not isinstance(enrichment.get("identifiers"), dict):
        enrichment["identifiers"] = {}

    # Steps 4+6: Routing & Escalation
    escalation_flag, escalation_reason = check_escalation(
        msg["raw_message"], category, confidence, enrichment.get("identifiers", {})
    )
    standard_queue    = ROUTING_TABLE.get(category, "Escalation")
    destination_queue = "Escalation" if escalation_flag else standard_queue
    routing_reason    = escalation_reason if escalation_flag else f"{category} routes to {destination_queue}"

    print(f"    → {destination_queue} | escalated={escalation_flag}")

    # Step 5: Summary — plain text
    summary_user = (
        f"Category: {category}\n"
        f"Priority: {priority}\n"
        f"Core Issue: {enrichment['core_issue']}\n"
        f"Identifiers: {json.dumps(enrichment['identifiers'])}\n"
        f"Urgency: {enrichment['urgency_signal']}\n"
        f"Queue: {destination_queue}\n"
        f"Escalated: {escalation_flag}"
        + (f"\nEscalation Reason: {escalation_reason}" if escalation_reason else "")
    )
    summary = call_text(client, SUMMARY_SYSTEM, summary_user)

    # Assemble — flat schema matching n8n output exactly
    return {
        "id":                record_id,
        "source":            msg["source"],
        "timestamp":         timestamp,
        "raw_message":       msg["raw_message"],
        "category":          category,
        "priority":          priority,
        "confidence_score":  confidence,
        "core_issue":        enrichment["core_issue"],
        "identifiers":       enrichment["identifiers"],
        "urgency_signal":    enrichment["urgency_signal"],
        "destination_queue": destination_queue,
        "routing_reason":    routing_reason,
        "escalation_flag":   escalation_flag,
        "escalation_reason": escalation_reason,
        "summary":           summary,
    }


def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set.")
        print("       Copy backend/.env.example to .env and add your Groq key.")
        print("       Get a free key at: https://console.groq.com")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)

    with open(INPUT_FILE) as f:
        messages = json.load(f)

    print(f"Processing {len(messages)} messages with {MODEL} (Groq)...\n")
    results = [process_message(client, msg) for msg in messages]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    escalated = sum(1 for r in results if r["escalation_flag"])
    print(f"\n✓ Done → {OUTPUT_FILE}")
    print(f"  {len(results)} records | {escalated} escalated | {len(results) - escalated} routed to standard queue")


if __name__ == "__main__":
    main()
