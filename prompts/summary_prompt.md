# Summary Generation Prompt — Step 5

## Prompt

```
You are writing an internal handoff note for the ArcVault support team. Given a fully
enriched support record, write a 2–3 sentence human-readable summary that the receiving
team will read before opening the ticket.

The summary should:
- State what the customer's issue or request is (use plain language, not jargon)
- Include the most important identifier(s) from the record (account, invoice number, etc.)
- End with a clear recommended action or next step for the receiving team

Tone: professional, direct, no filler phrases like "I hope this helps" or "Please let me know".

Record:
- Category: {{category}}
- Priority: {{priority}}
- Core Issue: {{core_issue}}
- Identifiers: {{identifiers}}
- Urgency Signal: {{urgency_signal}}
- Escalation Flag: {{escalation_flag}}
- Escalation Reason: {{escalation_reason}}
- Source: {{source}}

Return ONLY the summary text. No JSON, no labels, no markdown.
```

---

## Rationale

**Why generate a summary as a separate step:**

The summary is the human-facing output — the thing a support engineer reads in a Slack
notification or queue view before clicking into the full record. Generating it as a
separate prompt (rather than asking the classification prompt to also produce a summary)
means each prompt has one job. This makes prompts easier to iterate: if the summaries
are too long, I only need to touch this file.

**Passing the full enriched record rather than the raw message:**

The summary is built from the structured record, not re-derived from the raw message.
This ensures the summary is consistent with what was classified and enriched — it
can't contradict the routing decision. If the raw message were passed instead, the
model might re-classify in the summary ("this looks like a billing error...") even
if the classifier said something different.

**The recommended action requirement:**

Most AI-generated summaries end with a description of the problem and nothing else.
Adding "end with a clear recommended action" makes the summary actionable — the
receiving team knows what to do, not just what happened. This is especially valuable
for escalated tickets where the human reviewer may be unfamiliar with the context.

**Tone instruction:**

"No filler phrases" is a specific anti-pattern instruction. Without it, models
reliably produce summaries that end with "Please don't hesitate to reach out if you
need further assistance" — which reads as noise in an internal tool.

**Tradeoffs:**

Three sentences is a constraint, not a guideline. Some tickets (multi-issue, complex
billing disputes) genuinely need more context. The tradeoff is that the summary stays
scannable in queue views and Slack notifications. Longer summaries tend not to be read.

**What I'd change with more time:**

Generate summaries in the customer's language (detected from the raw message). ArcVault
serves international customers, and a summary in the wrong language is unhelpful to a
regional support team.
