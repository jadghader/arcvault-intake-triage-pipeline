# Enrichment Prompt — Step 3

## Purpose

Extract structured entities from the raw message to give the receiving team everything
they need to act immediately — without reading the original message. Output feeds directly
into Steps 4+6 (Routing & Escalation) and Step 5 (Summary).

---

## Implementation

**Model:** `llama-3.3-70b-versatile` (Groq, free tier)
**Endpoint:** `https://api.groq.com/openai/v1/chat/completions`
**JSON enforcement:** `response_format: { type: "json_object" }` — valid JSON guaranteed at API level
**Temperature:** `0.1` — low, for consistent entity extraction across runs

---

## Prompt (system + user)

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

Do not invent or infer values not stated in the message. If no identifiers are present, return an empty object {}.
```

### User message

```
Category: {category}
Priority: {priority}

Message:
{raw_message}
```

---

## Input Schema

| Field | Type | Source | Description |
|---|---|---|---|
| `category` | string | Step 2 output | Classification category — used to guide which identifiers to prioritise |
| `priority` | string | Step 2 output | Classification priority |
| `raw_message` | string | Step 1 output | Original customer message |

---

## Output Schema

```json
{
  "core_issue": "string",
  "identifiers": {
    "<key>": "string"
  },
  "urgency_signal": "string"
}
```

### Field constraints

| Field | Type | Constraints | Required |
|---|---|---|---|
| `core_issue` | string | One sentence. Must describe the actual problem or request, not restate the category. | Yes |
| `identifiers` | object | Dynamic key-value pairs. Only keys from the allowed vocabulary. Only values present in the message. Empty object `{}` if none found. | Yes |
| `urgency_signal` | string | One sentence. Must be grounded in message content — not a generic statement. | Yes |

### Allowed identifier keys

| Key | When to use |
|---|---|
| `account_id` | User or account identifier mentioned in the message |
| `invoice_number` | Invoice or order number |
| `error_code` | HTTP status code, error code, or error name |
| `affected_component` | Product feature or system component that is broken/slow |
| `feature_requested` | Name of the feature the customer is asking for |
| `integration_requested` | Third-party tool the customer wants to integrate |
| `incident_start` | Time or date the issue began |
| `billed_amount` | Dollar amount the customer was charged |
| `contracted_rate` | Dollar amount the customer's contract specifies |
| `discrepancy` | Difference between billed and contracted amount — used by escalation rule |
| `trigger_event` | Event that caused the issue (e.g., a recent platform update) |
| `scope` | How many users or accounts are affected |
| `use_case` | What the customer is trying to accomplish |
| `context` | Any other relevant context not covered by the above keys |

---

## Example outputs

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
    "billed_amount": "$1,240",
    "contracted_rate": "$980/month",
    "discrepancy": "$260"
  },
  "urgency_signal": "A confirmed billing discrepancy of $260 exists on a specific invoice — customer has already identified the exact amount."
}
```

### msg_002 — Feature Request (no identifiers)

```json
{
  "core_issue": "Customer wants a bulk export feature for audit logs to save time on compliance workflows.",
  "identifiers": {
    "feature_requested": "bulk export for audit logs",
    "use_case": "compliance reporting"
  },
  "urgency_signal": "Not urgent — this is a feature request with no active service disruption."
}
```

---

## Validation (Steps 4+6: Routing & Escalation node)

After the LLM responds, the Routing & Escalation Code node enforces:

1. `identifiers` must be an object — reset to `{}` if missing or wrong type
2. `discrepancy` value is parsed as a float (strips `$` and `,`) for the billing escalation rule
3. All three fields must be present — parse error thrown if missing

---

## Rationale

**Passing classification context into the enrichment prompt:**
The category tells the model which identifiers matter most. A `Billing Issue` message should surface `invoice_number` and `discrepancy`; an `Incident / Outage` should surface `affected_component` and `incident_start`. Without the category context, the model extracts whatever looks interesting rather than what the receiving team actually needs.

**Dynamic identifiers object instead of fixed schema:**
Messages vary widely — some have invoice numbers, some have error codes, some have neither. A fixed schema with nullable fields produces records full of `null` values. A dynamic key-value object with a controlled vocabulary produces only what is actually present, keeping output clean and actionable.

**"Do not invent values" instruction:**
Without this, models hallucinate plausible-looking values — inventing `account_id: "unknown"` or calculating `discrepancy: "$260"` by doing arithmetic on values in the message. The explicit instruction keeps output strictly grounded. The `discrepancy` calculation is the one borderline case: the model is allowed to compute it because it is directly derivable from values stated in the message, and it is needed for the billing escalation rule.

**`response_format: json_object` at the API level:**
Same reasoning as Step 2 — hard JSON enforcement at the API removes the need for markdown-stripping fallback logic in the parse node.

**Tradeoffs:**
The single-sentence `core_issue` constraint forces useful compression but loses nuance on complex messages that describe multiple issues. A `secondary_issue` field would handle this in production. The dynamic identifiers approach also means there is no guarantee a specific key will be present — downstream code must always use safe access (`identifiers?.discrepancy`) rather than assuming a key exists.

**What I'd change with more time:**
Add entity type detection — distinguish a user ID from an account ID, a charge from a discount. This would enable downstream automation (e.g., auto-querying the billing system for invoice #8821 before the Billing team even opens the ticket).
