# Summary Generation Prompt — Step 5

## Purpose

Generate a 2–3 sentence human-readable handoff note from the fully enriched record.
This is the human-facing output — what a support engineer reads in a queue view or
Slack notification before opening the ticket. It must be actionable, not just descriptive.

---

## Implementation

**Model:** `llama-3.3-70b-versatile` (Groq, free tier)
**Endpoint:** `https://api.groq.com/openai/v1/chat/completions`
**JSON enforcement:** None — output is plain text, not JSON
**Temperature:** `0.2` — slightly higher than Steps 2+3 to allow natural sentence variation

---

## Prompt (system + user)

### System message

```
You write internal handoff notes for the ArcVault support team. Write exactly 2-3 sentences. Professional, direct tone — no filler phrases like 'I hope this helps' or 'please let me know'. State the issue, include key identifiers, end with a concrete recommended action for the receiving team. Return only the summary text — no labels, no JSON.
```

### User message

```
Category: {category}
Priority: {priority}
Core Issue: {core_issue}
Identifiers: {identifiers}
Urgency: {urgency_signal}
Queue: {destination_queue}
Escalated: {escalation_flag}
Escalation Reason: {escalation_reason}
```

---

## Input Schema

| Field | Type | Source | Description |
|---|---|---|---|
| `category` | string | Step 2 output | Classification category |
| `priority` | string | Step 2 output | Classification priority |
| `core_issue` | string | Step 3 output | One-sentence problem summary |
| `identifiers` | object | Step 3 output | Extracted entities (invoice numbers, account IDs, etc.) |
| `urgency_signal` | string | Step 3 output | One-sentence urgency assessment |
| `destination_queue` | string | Steps 4+6 output | Routing destination |
| `escalation_flag` | boolean | Steps 4+6 output | Whether the record is escalated |
| `escalation_reason` | string \| null | Steps 4+6 output | Why it was escalated, if applicable |

---

## Output Schema

```json
{
  "summary": "string"
}
```

### Field constraints

| Field | Type | Constraints |
|---|---|---|
| `summary` | string | 2–3 sentences. Must name the issue, include at least one identifier if present, and end with a recommended action. No JSON, no labels, no markdown. |

---

## Example outputs

### msg_001 — Bug Report, High priority, not escalated

```
User jsmith (arcvault.io/user/jsmith) has been completely locked out with a 403 error
since last Tuesday's platform update. The issue is access-blocking and started
immediately after the deployment. Engineering should review the auth middleware changes
from that release and restore access for the affected account.
```

### msg_003 — Billing Issue, escalated ($260 discrepancy)

```
Invoice #8821 shows a charge of $1,240 against a contracted rate of $980/month,
resulting in a $260 overcharge that the customer has already identified. This record
has been escalated for human review due to the billing discrepancy exceeding the $200
threshold. Billing should verify the invoice against the customer's contract and issue
a correction or credit as appropriate.
```

### msg_005 — Incident / Outage, escalated (keyword + category)

```
The ArcVault dashboard has been down since approximately 2pm EST, with multiple users
confirmed affected — the customer has ruled out issues on their end. This is a confirmed
service incident and has been auto-escalated to the Escalation queue. Engineering should
check infrastructure health and dashboard service status immediately and open an incident
response if not already active.
```

---

## Rationale

**Summary generated as a separate step, not bundled with classification:**
Each prompt has one job. If summaries need tuning (too long, wrong tone, missing identifiers), only this prompt needs to change — the classification and enrichment prompts are untouched. Bundling all three outputs into one prompt makes individual iteration impossible.

**Built from the structured record, not the raw message:**
The summary is derived from what was classified and enriched, not re-derived from the raw message. This guarantees the summary cannot contradict the routing decision. If the raw message were passed instead, the model might re-classify in the summary ("this looks like a billing issue") even if the classifier assigned a different category.

**Escalation context passed explicitly:**
When `escalation_flag` is true, the `escalation_reason` is included in the user message. This lets the model reference the escalation in the summary ("escalated due to...") so the human reviewer immediately understands why the record landed in their queue — without having to inspect the structured fields.

**"End with a recommended action" requirement:**
Most AI-generated summaries describe the problem and stop. Adding this requirement makes the summary actionable — the receiving team knows what to do, not just what happened. This is especially valuable for escalated records where the reviewer may have no prior context.

**"No filler phrases" is a specific anti-pattern instruction:**
Without it, models reliably append "Please don't hesitate to reach out if you need further assistance" — which is noise in an internal tool and signals to the reader that the text was AI-generated without review.

**Temperature 0.2 instead of 0.1:**
Classification and enrichment need consistency — the same message should always get the same category. Summaries benefit from slight variation in sentence structure to read naturally rather than formulaically. 0.2 provides this without making output unpredictable.

**Tradeoffs:**
The 2–3 sentence constraint keeps summaries scannable in queue views and Slack alerts. Complex multi-issue tickets genuinely need more context, but longer summaries tend not to be read. The constraint is a deliberate product decision, not a prompt limitation.

**What I'd change with more time:**
Detect the customer's language from the raw message and generate the summary in that language. ArcVault serves international customers and a summary in the wrong language is unhelpful to a regional support team.
