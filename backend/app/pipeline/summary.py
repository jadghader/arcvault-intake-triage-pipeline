from agents import Agent, Runner
from pydantic import BaseModel
from app.schemas.pipeline import ClassificationResult, EnrichmentResult, RoutingResult
from app.config import resolve_model

SYSTEM_PROMPT = """\
You are writing an internal handoff note for the ArcVault support team.
Write a 2–3 sentence summary that the receiving team reads before opening the ticket.

Requirements:
- State what the customer's issue or request is (plain language)
- Include the most important identifier(s) if present
- End with a clear recommended next step for the receiving team
- If the record is escalated, mention that explicitly

Tone: professional, direct. No filler like "I hope this helps".
Return ONLY the summary text. No JSON, no labels."""


class _SummaryOutput(BaseModel):
    summary: str


def _make_agent(model: str) -> Agent:
    return Agent(
        name="SummaryAgent",
        instructions=SYSTEM_PROMPT,
        model=resolve_model(model),
        output_type=_SummaryOutput,
    )


async def generate_summary(
    source: str,
    classification: ClassificationResult,
    enrichment: EnrichmentResult,
    routing: RoutingResult,
    model: str,
) -> str:
    agent = _make_agent(model)
    identifiers_str = (
        ", ".join(f"{k}: {v}" for k, v in enrichment.identifiers.items()) or "none"
    )
    user_message = (
        f"Category: {classification.category}\n"
        f"Priority: {classification.priority}\n"
        f"Core Issue: {enrichment.core_issue}\n"
        f"Identifiers: {identifiers_str}\n"
        f"Urgency: {enrichment.urgency_signal}\n"
        f"Escalated: {routing.escalation_flag}\n"
        f"Escalation Reason: {routing.escalation_reason or 'N/A'}\n"
        f"Queue: {routing.destination_queue}\n"
        f"Source: {source}"
    )
    result = await Runner.run(agent, user_message)
    output = result.final_output
    return output.summary
