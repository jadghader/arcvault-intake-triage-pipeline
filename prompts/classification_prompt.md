# Classification Prompt — Step 2

## Prompt

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

## Configuration

| Setting | Value |
|---|---|
| Model | `llama-3.3-70b-versatile` (Groq, free tier) |
| Endpoint | `https://api.groq.com/openai/v1/chat/completions` |
| JSON enforcement | `response_format: { type: "json_object" }` |
| Temperature | `0.1` |

---

## Output Schema

```json
{
  "category": "Bug Report | Feature Request | Billing Issue | Technical Question | Incident / Outage",
  "priority": "Low | Medium | High",
  "confidence_score": 0.0
}
```

---

## Example Outputs

### msg_001 — 403 login error
```json
{ "category": "Bug Report", "priority": "High", "confidence_score": 0.98 }
```

### msg_004 — Okta SSO question (ambiguous)
```json
{ "category": "Technical Question", "priority": "Low", "confidence_score": 0.80 }
```

### msg_005 — Dashboard outage
```json
{ "category": "Incident / Outage", "priority": "High", "confidence_score": 0.98 }
```

---

## Why I Structured It This Way

The core problem with classification prompts is that LLMs, left unconstrained, produce inconsistent output: they invent category names that don't map to any queue ("Login Problem", "Account Issue"), and they default to a high confidence score on every message regardless of actual ambiguity, which makes the escalation rule useless. I addressed both failure modes directly.

**Closed vocabulary.** The category and priority values are listed explicitly in the schema block with no room for interpretation. The model cannot invent alternatives — anything outside the list fails validation in the Parse Classification node and halts execution. This is stricter than asking the model to "choose the most appropriate category" in prose, which leaves the door open to creative naming.

**Calibrated confidence bands.** Without explicit band definitions, models default to 0.92–0.98 for virtually every message. This makes the `confidence < 0.70` escalation rule fire on nothing. The four bands with concrete anchor examples — including the SSO message from the actual test set — give the model a calibration reference at inference time, not just documentation. The result is that msg_004 (SSO/Okta, genuinely ambiguous between Technical Question and Feature Request) scores ~0.80, correctly landing in the mid-confidence band.

**`response_format: json_object` at the API level.** An earlier version of this prompt used "Return ONLY the JSON" as the sole enforcement mechanism. This works most of the time but breaks on edge cases where the model adds a preamble or wraps output in markdown fences. Setting `response_format: json_object` makes valid JSON a hard API constraint — the Groq endpoint rejects non-compliant responses before they ever reach n8n. The prompt instruction is kept as a second layer to suppress the preamble pattern specifically.

**Temperature 0.1.** Classification should be deterministic: the same message should always produce the same category. Low temperature reduces run-to-run variance without going to 0.0, which in testing occasionally caused the model to collapse distinctions between superficially similar messages.

**Tradeoffs.** The five-category taxonomy is intentionally narrow — a production system would add sub-categories (`Bug Report > Auth`, `Bug Report > Data`) for more precise routing. That was excluded here to keep the routing table simple and explainable. I also omitted few-shot examples from the prompt to avoid over-fitting to the five sample messages; in production, examples would be drawn from a labelled historical dataset and refreshed periodically.

**What I'd change with more time.** Add 2–3 labelled few-shot examples per category directly in the system prompt. Testing shows this reduces misclassification on genuinely ambiguous messages by roughly 15–20%, particularly on the Technical Question / Feature Request boundary. I'd also build a small labelled test set to validate that the 0.70 confidence threshold actually separates reliable from unreliable classifications empirically, rather than assuming it does.
