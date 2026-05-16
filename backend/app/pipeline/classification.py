import json
import litellm
from app.schemas.pipeline import ClassificationResult

VALID_CATEGORIES = {
    "Bug Report", "Feature Request", "Billing Issue",
    "Technical Question", "Incident / Outage",
}
VALID_PRIORITIES = {"Low", "Medium", "High"}

PROMPT = """\
You are a B2B SaaS support triage specialist for ArcVault. Classify the inbound message.

Return a JSON object with exactly these fields:
{{
  "category": "<one of: Bug Report | Feature Request | Billing Issue | Technical Question | Incident / Outage>",
  "priority": "<one of: Low | Medium | High>",
  "confidence_score": <float 0.0–1.0>
}}

Priority guidelines:
- High: service disruption, billing errors, security issues, blocked access
- Medium: degraded functionality, feature requests with clear business impact
- Low: general inquiries, pre-sales, minor UX feedback

Confidence guidelines:
- 0.90–1.0: clearly matches one category, no ambiguity
- 0.70–0.89: likely correct, some signals point elsewhere
- 0.50–0.69: genuinely ambiguous
- Below 0.50: insufficient information

Return ONLY the JSON. No explanation, no markdown fences.

Message:
{message}"""


async def classify(raw_message: str, model: str) -> ClassificationResult:
    prompt = PROMPT.format(message=raw_message)
    response = await litellm.acompletion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
        temperature=0,
    )
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()

    data = json.loads(text)

    if data["category"] not in VALID_CATEGORIES:
        raise ValueError(f"Unexpected category: {data['category']}")
    if data["priority"] not in VALID_PRIORITIES:
        raise ValueError(f"Unexpected priority: {data['priority']}")

    return ClassificationResult(
        category=data["category"],
        priority=data["priority"],
        confidence_score=float(data["confidence_score"]),
    )
