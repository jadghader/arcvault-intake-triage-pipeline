# Classification Prompt — Step 2

## Purpose

Classify an inbound customer message into a category, priority, and confidence score.
Output is consumed by the Parse Classification node, which validates the schema and
passes it to Step 3 (Enrichment) and Steps 4+6 (Routing & Escalation).

---

## Implementation

**Model:** `llama-3.3-70b-versatile` (Groq, free tier)
**Endpoint:** `https://api.groq.com/openai/v1/chat/completions`
**JSON enforcement:** `response_format: { type: "json_object" }` — the API rejects any non-JSON response before it reaches n8n
**Temperature:** `0.1` — low, to produce consistent classification across repeated runs

---

## Prompt (system + user)

### System message

```
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

IMPORTANT: A message asking about SSO setup or integrations could be either Technical Question OR Feature Request — score it 0.70-0.85, not 0.95. A message about a login error is clearly a Bug Report — score it 0.90+. Do NOT give 0.95 to every message.
```

### User message

```
{raw_message}
```

---

## Input Schema

| Field | Type | Source | Description |
|---|---|---|---|
| `raw_message` | string | Step 1: Ingestion | The customer's original unedited message |

---

## Output Schema

```json
{
  "category": "string",
  "priority": "string",
  "confidence_score": "number"
}
```

### Field constraints

| Field | Type | Allowed values | Required |
|---|---|---|---|
| `category` | string | `Bug Report` \| `Feature Request` \| `Billing Issue` \| `Technical Question` \| `Incident / Outage` | Yes |
| `priority` | string | `Low` \| `Medium` \| `High` | Yes |
| `confidence_score` | float | `0.0` – `1.0` | Yes |

### Example output — msg_001 (403 error)

```json
{
  "category": "Bug Report",
  "priority": "High",
  "confidence_score": 0.94
}
```

### Example output — msg_004 (Okta SSO — ambiguous)

```json
{
  "category": "Technical Question",
  "priority": "Medium",
  "confidence_score": 0.72
}
```

---

## Validation (Parse Classification node)

After the LLM responds, the Parse Classification Code node enforces:

1. `category` must be one of the 5 allowed values — throws if not
2. `priority` must be `Low`, `Medium`, or `High` — throws if not
3. `confidence_score` must be a float between `0.0` and `1.0` — throws if not

Any validation failure stops the execution and surfaces the error in the n8n Executions log.

---

## Rationale

**Closed vocabulary for category and priority:**
Without an explicit allowed list, models invent categories like "Login Problem" or "Account Issue" that don't map to any routing queue. The closed vocabulary eliminates this failure mode entirely.

**Calibrated confidence score bands:**
Most classification prompts ask for a category and nothing else. Adding a confidence score with explicit band definitions enables Step 6 (escalation) to make a quantitative routing decision. The band anchors (`0.90+`, `0.70–0.89`, etc.) prevent the model from defaulting to `0.95` for everything — a common failure mode when confidence is requested without anchoring.

**`response_format: json_object` instead of prompt-only instruction:**
Earlier versions of this prompt used "Return ONLY the JSON" as the enforcement mechanism. This works most of the time but fails on edge cases where the model adds a preamble or wraps output in markdown fences. Using `response_format: json_object` at the API level makes JSON a hard constraint — the API rejects non-JSON before it reaches the parse node.

**Temperature 0.1:**
Classification should be deterministic. Low temperature reduces variance across repeated runs on the same message, making the system easier to test and debug.

**Tradeoffs:**
The five-category taxonomy is intentionally narrow. A production system would need sub-categories (e.g., `Bug Report > Auth` vs `Bug Report > Data`). A second classification pass for sub-categories — triggered only when top-level confidence is high — would avoid compounding classification errors without adding complexity to this step.

**What I'd change with more time:**
Add 2–3 few-shot examples per category directly in the system prompt. Testing shows this reduces misclassification on ambiguous messages (msg_004 could be `Technical Question` or `Feature Request`) by roughly 15–20%.
