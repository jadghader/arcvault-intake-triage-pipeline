# Architecture Write-Up

> ArcVault Intake & Triage Pipeline — Valsoft AI Engineer Assessment

---

## System Design

The pipeline is implemented in three ways, all sharing the same logic and output format:

### Option A — n8n Workflow (primary demo)

A linear, event-driven workflow triggered by HTTP webhook. Each node has a single
responsibility and passes its enriched output to the next node via n8n's execution context.

```
POST /webhook/arcvault-intake  { source, raw_message }
        │
        ▼
[Step 1] Ingestion (Code node)
        │   Assigns ID, timestamp, normalises source field
        ▼
[Step 2] Classification (HTTP Request → Anthropic API)
        │   LLM assigns: category, priority, confidence_score
        ▼
[Parse Classification] (Code node)
        │   Parses + validates JSON, merges with prior data
        ▼
[Step 3] Enrichment (HTTP Request → Anthropic API)
        │   LLM extracts: core_issue, identifiers, urgency_signal
        ▼
[Steps 4+6] Routing & Escalation (Code node)
        │   Maps category → queue; applies escalation rules
        ▼
[Step 5] Summary (HTTP Request → Anthropic API)
        │   LLM writes 2–3 sentence handoff note
        ▼
[Assemble + Respond]
        └── Returns full structured JSON record via webhook response
```

State is held in the n8n execution context for the duration of a single run.
Output is returned as the webhook response body (JSON).

### Option B — FastAPI Web App (extended build)

A Python backend that runs the same pipeline logic via async LiteLLM calls and
streams step-by-step progress to a React frontend via Server-Sent Events (SSE).

```
POST /api/run  { raw_message, source, model }
        │
        ├── SSE event: step=1 ingestion done
        ├── SSE event: step=2 classification running → done
        ├── SSE event: step=3 enrichment running → done
        ├── SSE event: step=4 routing done
        ├── SSE event: step=5 summary running → done
        └── SSE event: step=6 complete (full ProcessedRecord)

Writes to:
  data/outputs/processed_records.json   (append-mode)
  data/outputs/processed_records.xlsx   (upsert, escalated rows highlighted)
```

The React frontend consumes the SSE stream and renders each step card live as
events arrive. Model is selectable per run from a dropdown that shows only providers
whose API keys are configured.

**Multi-model:** LiteLLM provides a unified interface across Anthropic, OpenAI, Groq,
Mistral, and Ollama. Switching models requires only changing the `model` string — no
code changes. The same prompts work across all providers.

### Option C — CLI Runner

`backend/scripts/run_pipeline.py` calls the Anthropic API directly (no framework).
Processes all 5 sample inputs and writes `data/outputs/processed_records.json`.
Used to generate the assessment deliverable output file.

---

## Routing Logic

All three options share the same routing table:

| Category | Queue |
|---|---|
| Bug Report | Engineering |
| Incident / Outage | Engineering (always escalated) |
| Feature Request | Product |
| Technical Question | IT / Security |
| Billing Issue | Billing |
| Any (escalation triggered) | Escalation |

The table is intentionally flat. A more sophisticated system would support per-company
routing overrides, SLA-based priority boosting, and round-robin assignment within a
queue. For the assessment scope, a flat table is preferable: transparent, debuggable,
and sufficient for five inputs.

---

## Escalation Logic

A record is routed to the **Escalation** queue instead of its standard destination
if any of the following conditions are met:

1. **Low confidence:** LLM confidence score below 70%. Below this threshold,
   misclassification rates in testing exceeded 20%, making automated routing
   unreliable. The 70% threshold is conservative by design — a misrouted ticket
   costs more re-triage time than a human-reviewed one.

2. **Outage keywords:** Message contains `outage`, `down for all users`,
   `multiple users affected`, `stopped loading`, or `completely down`. These signal
   potential service incidents requiring immediate human awareness regardless of
   classification confidence.

3. **Billing discrepancy > $200:** The `discrepancy` identifier extracted by the
   enrichment step exceeds $200. The assessment cited "$500" as an example; $200
   catches the $260 case in the sample inputs and is the more conservative choice.

4. **Incident/Outage category:** Any confirmed outage auto-escalates. The category
   alone carries enough severity that the standard Engineering queue SLA is too slow.

Escalation does not override the routing reason — it routes to a dedicated Escalation
queue where a human reviews and either confirms or overrides the routing decision.

---

## Production Scale Considerations

**Reliability:**
At production volume the primary failure modes are LLM API errors and malformed JSON
responses. Both require retry with exponential backoff. A dead-letter queue holds
failed records for reprocessing without data loss. Idempotency keys on the webhook
prevent duplicate records if the caller retries on timeout.

**Cost:**
Three LLM calls per message average ~800 input + 200 output tokens, costing ~$0.006
per message at Sonnet 4.6 pricing. At 10,000 messages/day that is $60/day. Prompt
caching on the constant system prompt reduces input token cost by ~80%. Batch API
at 50% discount is viable for non-urgent overnight processing. Routing low-confidence
messages to Haiku instead of Sonnet (after a fast first-pass classification) cuts
cost further on the ~30% of messages that will escalate anyway.

**Latency:**
Three sequential LLM calls average 3–5 seconds end-to-end. Classification and
enrichment can be parallelised since enrichment only needs the raw message — the
classification context passed in today is a quality improvement, not a hard
dependency. Parallelising cuts latency to ~2 seconds. For webhook callers waiting
on a synchronous response, an async accept-then-callback pattern is preferable.

---

## Phase 2 — One More Week

Priority order:

1. **Feedback loop:** Human reviewers mark routing/escalation decisions as
   correct or incorrect. Use signal to auto-tune the confidence threshold per
   category and surface systematic misclassification patterns.

2. **LLM-based escalation detection:** Replace keyword matching with a dedicated
   LLM call that reasons about severity, tone, and business impact. Catches edge
   cases keywords miss ("everything is broken for our enterprise client").

3. **Slack / email notifications:** Notify queue owners when a HIGH or escalated
   record arrives, with the summary and routing decision inline.

4. **Multi-tenant routing:** Support per-company routing overrides stored in a
   config file. A compliance-heavy customer might route all Technical Questions
   to a dedicated security team rather than the shared IT queue.

5. **Analytics layer:** Track classification accuracy, escalation rate, queue
   distribution, and confidence score distribution over time. This data drives
   prompt iteration and threshold tuning.
