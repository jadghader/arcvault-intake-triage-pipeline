# Enrichment Prompt — Step 3

## Prompt

### System message

```
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
- "discrepancy" must be a numeric dollar amount as a plain number string, e.g. "260" not "charge exceeds contract rate". Calculate it from billed_amount minus contracted_rate if both are present in the message.
```

### User message

```
Category: {category}
Priority: {priority}

Message:
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
  "core_issue": "string — one sentence describing the actual problem or request",
  "identifiers": {
    "key": "value — only keys from the allowed vocabulary, only values present in the message"
  },
  "urgency_signal": "string — one sentence grounded in message content"
}
```

**Allowed identifier keys:**

| Key | When to extract |
|---|---|
| `account_id` | User or account identifier mentioned in the message |
| `invoice_number` | Invoice or order number |
| `error_code` | HTTP status code, error code, or error name |
| `affected_component` | Product feature or system that is broken or slow |
| `feature_requested` | Name of the feature the customer is asking for |
| `integration_requested` | Third-party tool the customer wants to integrate |
| `incident_start` | Time or date the issue began |
| `billed_amount` | Dollar amount the customer was charged |
| `contracted_rate` | Dollar amount the customer's contract specifies |
| `discrepancy` | Numeric difference between billed and contracted amount — drives the billing escalation rule |
| `trigger_event` | Event that caused the issue (e.g., a recent platform update) |
| `scope` | How many users or accounts are affected |
| `use_case` | What the customer is trying to accomplish |
| `context` | Any other relevant context not covered by the above keys |

---

## Example Outputs

### msg_001 — Bug Report (403 error)

```json
{
  "core_issue": "User is unable to log in due to a 403 error that started after last Tuesday's platform update.",
  "identifiers": {
    "account_id": "arcvault.io/user/jsmith",
    "error_code": "403",
    "trigger_event": "platform update last Tuesday"
  },
  "urgency_signal": "Access is completely blocked for the user — this is an active, ongoing login failure."
}
```

### msg_003 — Billing Issue ($260 discrepancy)

```json
{
  "core_issue": "Customer was charged $1,240 but their contracted monthly rate is $980, resulting in a $260 overcharge.",
  "identifiers": {
    "invoice_number": "8821",
    "billed_amount": "1240",
    "contracted_rate": "980",
    "discrepancy": "260"
  },
  "urgency_signal": "A confirmed billing discrepancy of $260 exists on a specific invoice — customer has already identified the exact amount."
}
```

### msg_005 — Incident / Outage (dashboard down)

```json
{
  "core_issue": "The ArcVault dashboard stopped loading at 2pm EST and multiple users are currently affected.",
  "identifiers": {
    "affected_component": "dashboard",
    "incident_start": "2pm EST",
    "scope": "multiple users affected"
  },
  "urgency_signal": "Active service outage affecting multiple users with no resolution — customer has already ruled out issues on their end."
}
```

---

## Why I Structured It This Way

The enrichment step has one job: give the receiving team everything they need to act on the ticket without reading the original message. The design decisions all serve that goal.

**Passing classification context into the user message.** The category and priority from Step 2 are included in the user message so the model knows which identifiers matter most. A `Billing Issue` should surface `invoice_number` and `discrepancy`; an `Incident / Outage` should surface `affected_component` and `incident_start`. Without this context, the model extracts whatever looks interesting rather than what is actionable for the specific receiving team. This is also why enrichment is a separate step from classification — by the time enrichment runs, the category decision has already been made and can be used as guidance.

**Dynamic identifiers object instead of a fixed schema.** Messages vary widely — some have invoice numbers, some have error codes, some have neither. A fixed schema with nullable fields produces records full of `null` values that add noise without information. A dynamic key-value object with a controlled vocabulary produces only what is actually present in the message, keeping output clean. The controlled vocabulary (14 allowed keys) prevents the model from inventing freeform keys while still covering the realistic range of B2B support message types.

**"Do not invent values" instruction.** Without this explicit constraint, models hallucinate plausible-looking values — filling `account_id: "unknown"` when no account ID is mentioned, or inventing an error code. The instruction keeps all extracted values strictly grounded in the message text. The one deliberate exception is `discrepancy`: the model is allowed — and instructed — to calculate it from `billed_amount` minus `contracted_rate` when both are stated. This is the only derived value, and it exists because the billing escalation rule in Step 4+6 needs a numeric amount to compare against the $200 threshold.

**`response_format: json_object` at the API level.** Same reasoning as Step 2 — hard JSON enforcement at the API removes the need for markdown-stripping or fallback logic in the downstream parse node. The Groq endpoint rejects non-compliant responses before they reach n8n.

**Tradeoffs.** The single-sentence `core_issue` constraint forces useful compression but loses nuance when a message describes multiple issues. A `secondary_issue` field would handle this in production. The dynamic identifiers approach also means there is no guarantee a specific key is present — downstream code must always use safe access (`identifiers?.discrepancy`) rather than assuming the key exists.

**What I'd change with more time.** Add entity type detection to distinguish between similar identifier types — for example, differentiating a user ID from an account ID, or a one-time charge from a recurring rate. This would enable downstream automation: auto-querying the billing system for invoice #8821 before the Billing team even opens the ticket, or pre-populating the account context for the engineering team from the account ID. I'd also add a validation step that checks whether the extracted `discrepancy` value mathematically matches `billed_amount - contracted_rate`, catching cases where the model makes an arithmetic error.
