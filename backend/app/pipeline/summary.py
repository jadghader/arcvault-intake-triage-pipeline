import litellm
from app.schemas.pipeline import ClassificationResult, EnrichmentResult, RoutingResult

PROMPT = """\
You are writing an internal handoff note for the ArcVault support team.
Write a 2–3 sentence summary that the receiving team reads before opening the ticket.

Requirements:
- State what the customer's issue or request is (plain language)
- Include the most important identifier(s) if present
- End with a clear recommended next step for the receiving team

Tone: professional, direct. No filler like "I hope this helps".

Record:
- Category: {category}
- Priority: {priority}
- Core Issue: {core_issue}
- Identifiers: {identifiers}
- Urgency: {urgency_signal}
- Escalated: {escalated}
- Source: {source}

Return ONLY the summary text. No JSON, no labels."""


async def generate_summary(
    source: str,
    classification: ClassificationResult,
    enrichment: EnrichmentResult,
    routing: RoutingResult,
    model: str,
) -> str:
    prompt = PROMPT.format(
        category=classification.category,
        priority=classification.priority,
        core_issue=enrichment.core_issue,
        identifiers=", ".join(f"{k}: {v}" for k, v in enrichment.identifiers.items()) or "none",
        urgency_signal=enrichment.urgency_signal,
        escalated=routing.escalation_flag,
        source=source,
    )
    response = await litellm.acompletion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
