from agents import Agent, Runner
from app.schemas.pipeline import ClassificationResult, EnrichmentResult

SYSTEM_PROMPT = """\
You are a support data analyst for ArcVault. You always respond with valid JSON only — no markdown, no explanation.

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

IMPORTANT rules for identifiers:
- Do not invent or infer values not stated in the message
- If no identifiers are present, return an empty object {}
- "discrepancy" must be a numeric dollar amount as a plain number string, e.g. "260" not "charge exceeds contract rate". Calculate it from billed_amount minus contracted_rate if both are present in the message."""


def _make_agent(model: str) -> Agent:
    return Agent(
        name="EnrichmentAgent",
        instructions=SYSTEM_PROMPT,
        model=model,
        output_type=EnrichmentResult,
    )


async def enrich(
    raw_message: str, classification: ClassificationResult, model: str
) -> EnrichmentResult:
    agent = _make_agent(model)
    user_message = f"Category: {classification.category}\nPriority: {classification.priority}\n\nMessage:\n{raw_message}"
    result = await Runner.run(agent, user_message)
    output = result.final_output
    return EnrichmentResult(
        core_issue=output.core_issue,
        identifiers={k: str(v) for k, v in output.identifiers.items()},
        urgency_signal=output.urgency_signal,
    )
