import json
import litellm
from app.schemas.pipeline import ClassificationResult, EnrichmentResult

PROMPT = """\
You are a support data analyst for ArcVault. Extract structured information from the message.

Classification context:
- Category: {category}
- Priority: {priority}

Return a JSON object with exactly these fields:
{{
  "core_issue": "<one sentence: what the customer's actual problem or request is>",
  "identifiers": {{
    "<key>": "<value>"
  }},
  "urgency_signal": "<one sentence: why this is or isn't urgent>"
}}

Only include identifiers actually present in the message. Possible keys:
account_id, invoice_number, error_code, affected_component, feature_requested,
integration_requested, incident_start, billed_amount, contracted_rate, discrepancy,
trigger_event, scope, use_case, context

Do NOT invent values. Omit any key with no value in the message.
Return ONLY the JSON. No explanation, no markdown fences.

Message:
{message}"""


async def enrich(
    raw_message: str, classification: ClassificationResult, model: str
) -> EnrichmentResult:
    prompt = PROMPT.format(
        category=classification.category,
        priority=classification.priority,
        message=raw_message,
    )
    response = await litellm.acompletion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        temperature=0,
    )
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()

    data = json.loads(text)
    return EnrichmentResult(
        core_issue=data["core_issue"],
        identifiers={k: str(v) for k, v in data.get("identifiers", {}).items()},
        urgency_signal=data["urgency_signal"],
    )
