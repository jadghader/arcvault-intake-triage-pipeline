# Enrichment Prompt — Step 3

## Prompt

```
You are a support data analyst for ArcVault. Given a customer message and its classification,
extract structured information to help the receiving team act on it immediately.

Classification context:
- Category: {{category}}
- Priority: {{priority}}

Return a JSON object with exactly these fields:

{
  "core_issue": "<one sentence: what the customer's actual problem or request is>",
  "identifiers": {
    "<key>": "<value>"
    // Include only identifiers actually present in the message.
    // Possible keys: account_id, invoice_number, error_code, affected_component,
    //                feature_requested, integration_requested, incident_start,
    //                billed_amount, contracted_rate, discrepancy, trigger_event,
    //                scope, use_case, context
    // Omit any key that has no value in the message. Do not invent values.
  },
  "urgency_signal": "<one sentence: why this is or isn't urgent, based on message content>"
}

Return ONLY the JSON object. No explanation, no markdown, no preamble.

Message:
{{raw_message}}
```

---

## Rationale

**Why pass classification context into the enrichment prompt:**

The enrichment step receives the classification output from Step 2. Passing `category` and
`priority` into the prompt lets the model prioritize which identifiers to extract. A
"Billing Issue" message should surface `invoice_number` and `discrepancy`; an "Incident"
message should surface `affected_component` and `incident_start`. Without this context,
the model extracts whatever looks interesting rather than what the receiving team needs.

**The open-ended identifiers object:**

Rather than forcing a fixed schema for identifiers, the prompt uses a dynamic key-value
approach with a suggested key vocabulary. This handles the reality that messages vary
widely — some have invoice numbers, some have error codes, some have neither. A fixed
schema with nullable fields produces records full of `null` values that look messy in
the output; a dynamic object produces only what's actually there.

**"Do not invent values" instruction:**

This is the single most important safety instruction in the prompt. Without it, models
will hallucinate plausible-looking values (e.g., inferring `discrepancy: "$260"` by
doing math, which is actually fine, but also inventing `account_id: "unknown"` or
`error_code: "500"` when none was mentioned). The explicit instruction keeps the
output grounded in the message.

**Tradeoffs:**

The single-sentence `core_issue` constraint is intentional — it forces compression that
makes the output useful in a queue notification or Slack alert. The downside is that
complex messages (e.g., a message describing both a bug AND a billing issue) lose
nuance. In production, a `secondary_issue` field would handle this.

**What I'd change with more time:**

Add entity type detection — distinguish between a user ID and an account ID, between
a dollar amount that's a charge vs a discount. This would enable downstream automation
(e.g., auto-querying the billing system for invoice #8821 before the Billing team
even opens the ticket).
