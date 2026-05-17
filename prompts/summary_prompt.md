# Summary Generation Prompt — Step 5

## Prompt

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

## Configuration

| Setting | Value |
|---|---|
| Model | `llama-3.3-70b-versatile` (Groq, free tier) |
| Endpoint | `https://api.groq.com/openai/v1/chat/completions` |
| JSON enforcement | None — output is plain text |
| Temperature | `0.2` |

---

## Output

Plain text. 2–3 sentences. Must name the issue, include at least one identifier if present, and end with a concrete recommended action. No JSON, no labels, no markdown.

---

## Example Outputs

### msg_001 — Bug Report, High priority, not escalated

```
User jsmith (arcvault.io/user/jsmith) has been completely locked out with a 403 error since last Tuesday's platform update. The issue is access-blocking and started immediately after the deployment. Engineering should review the auth middleware changes from that release and restore access for the affected account.
```

### msg_003 — Billing Issue, escalated ($260 discrepancy)

```
Invoice #8821 shows a charge of $1,240 against a contracted rate of $980/month, resulting in a $260 overcharge that the customer has already identified. This record has been escalated for human review due to the billing discrepancy exceeding the $200 threshold. Billing should verify the invoice against the customer's contract and issue a correction or credit as appropriate.
```

### msg_005 — Incident / Outage, escalated (keyword + category)

```
The ArcVault dashboard has been down since approximately 2pm EST, with multiple users confirmed affected — the customer has ruled out issues on their end. This is a confirmed service incident and has been auto-escalated to the Escalation queue. Engineering should check infrastructure health and dashboard service status immediately and open an incident response if not already active.
```

---

## Why I Structured It This Way

The summary is the human-facing output of the entire pipeline — it is what a support engineer reads in a queue view or Slack notification before opening the ticket. It needs to be immediately actionable, not just descriptive. Every design decision in this prompt serves that goal.

**Built from the structured record, not the raw message.** The user message passes the already-classified and enriched fields — category, core issue, identifiers, escalation status — rather than the raw customer text. This guarantees the summary cannot contradict the routing decision. If the raw message were passed instead, the model might re-interpret the message independently and produce a summary that conflicts with the classification ("this looks like a billing issue") even when a different category was assigned. Deriving the summary from the structured record locks it to the pipeline's decisions.

**Escalation context passed explicitly.** When `escalation_flag` is true, the `escalation_reason` is included in the user message. This lets the model reference the escalation directly in the summary ("escalated due to billing discrepancy exceeding the $200 threshold") so a human reviewer immediately understands why the record landed in their queue — without having to inspect the JSON fields. Without this, escalated summaries look identical to non-escalated ones, which defeats the purpose of the escalation queue.

**"End with a concrete recommended action" instruction.** Most AI-generated summaries describe the problem and stop. A support engineer reading the summary already knows there is a problem — they need to know what to do next. The required action sentence ("Engineering should review the auth middleware changes...") makes the summary a decision-support tool rather than a description. This is especially valuable for escalated records where the reviewer may have no prior context on the ticket.

**"No filler phrases" as an explicit anti-pattern instruction.** Without it, models reliably append "Please don't hesitate to reach out if you need further assistance" or "I hope this helps" — which is noise in an internal tool and immediately signals to the reader that the text was AI-generated without review. Naming the specific phrases to avoid is more reliable than a generic instruction to "be professional."

**Plain text output, no JSON enforcement.** Steps 2 and 3 use `response_format: json_object` because their outputs are parsed and validated programmatically. The summary is consumed directly by humans — there is no parse step. Forcing it through a JSON wrapper adds unnecessary extraction logic and makes the output less natural to read. Plain text is the right format here.

**Temperature 0.2 instead of 0.1.** Classification and enrichment need to be deterministic — the same message should always get the same category and the same extracted identifiers. Summaries benefit from slight variation in sentence structure so that five records processed in sequence don't all read like copies of the same template. 0.2 provides this without making the output unpredictable or inconsistent in tone.

**Tradeoffs.** The 2–3 sentence constraint keeps summaries scannable in queue views and Slack alerts, but it compresses complex multi-issue tickets more than is ideal. A ticket describing both a login failure and a suspected billing discrepancy genuinely needs more context. The constraint is a deliberate product decision — longer summaries tend not to be read in high-volume queue environments — but it means some nuance is lost for edge cases.

**What I'd change with more time.** Detect the customer's language from the raw message and generate the summary in that language. For a company serving international customers, routing a ticket to a regional support team with the summary in English is only marginally better than no summary at all. I would also add a tone-detection pass: if the raw message contains elevated language ("this is completely unacceptable", "we are considering cancelling"), the summary should flag the customer sentiment explicitly so the receiving team can calibrate their response accordingly.
