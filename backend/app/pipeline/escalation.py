from app.schemas.pipeline import ClassificationResult, EnrichmentResult

CONFIDENCE_THRESHOLD = 0.70
BILLING_THRESHOLD = 200.0

ESCALATION_KEYWORDS = [
    "outage",
    "down for all users",
    "multiple users affected",
    "not loading",
    "stopped loading",
    "completely down",
]


def check_escalation(
    raw_message: str,
    classification: ClassificationResult,
    enrichment: EnrichmentResult,
) -> tuple[bool, str | None]:
    if classification.confidence_score < CONFIDENCE_THRESHOLD:
        pct = f"{classification.confidence_score:.0%}"
        return True, f"Confidence {pct} below {CONFIDENCE_THRESHOLD:.0%} threshold"

    msg_lower = raw_message.lower()
    for kw in ESCALATION_KEYWORDS:
        if kw in msg_lower:
            return True, f"Escalation keyword matched: '{kw}'"

    disc = enrichment.identifiers.get("discrepancy", "")
    if disc:
        try:
            amount = float(disc.replace("$", "").replace(",", "").strip())
            if amount > BILLING_THRESHOLD:
                return True, f"Billing discrepancy ${amount:.0f} exceeds ${BILLING_THRESHOLD:.0f} threshold"
        except ValueError:
            pass

    if classification.category == "Incident / Outage":
        return True, "Incident / Outage category auto-escalates"

    return False, None
