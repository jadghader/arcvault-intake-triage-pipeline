from agents import Agent, Runner
from pydantic import field_validator
from app.schemas.pipeline import ClassificationResult
from app.config import resolve_model

VALID_CATEGORIES = {
    "Bug Report", "Feature Request", "Billing Issue",
    "Technical Question", "Incident / Outage",
}
VALID_PRIORITIES = {"Low", "Medium", "High"}

SYSTEM_PROMPT = """\
You are a B2B SaaS support triage specialist for ArcVault. You always respond with valid JSON only — no markdown, no explanation.

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

Confidence score rules — you MUST use the full range, not default to 0.95:
- 0.90-1.0: message fits exactly one category with no ambiguity whatsoever
- 0.70-0.89: likely correct but the message has signals that could point to another category
- 0.50-0.69: genuinely ambiguous — two categories are both plausible
- below 0.50: insufficient information to classify reliably

IMPORTANT: A message asking about SSO setup or integrations could be either Technical Question OR Feature Request — score it 0.70-0.85, not 0.95. A message about a login error is clearly a Bug Report — score it 0.90+. Do NOT give 0.95 to every message."""


class _ValidatedClassification(ClassificationResult):
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(f"Unexpected category: {v}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in VALID_PRIORITIES:
            raise ValueError(f"Unexpected priority: {v}")
        return v

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence_score must be 0.0–1.0, got {v}")
        return v


def _make_agent(model: str) -> Agent:
    return Agent(
        name="ClassificationAgent",
        instructions=SYSTEM_PROMPT,
        model=resolve_model(model),
        output_type=_ValidatedClassification,
    )


async def classify(raw_message: str, model: str) -> ClassificationResult:
    agent = _make_agent(model)
    result = await Runner.run(agent, raw_message)
    output = result.final_output
    return ClassificationResult(
        category=output.category,
        priority=output.priority,
        confidence_score=output.confidence_score,
    )
