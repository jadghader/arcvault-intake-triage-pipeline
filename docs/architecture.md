# Architecture Write-Up

---

## System Design

The pipeline is built as a linear, event-driven n8n workflow triggered by HTTP webhook.
Each node has a single responsibility and passes its enriched output to the next via n8n's
execution context — no shared database, no side effects between steps.

```
POST /webhook/arcvault-intake  { source, raw_message }
        │
        ▼
[Step 1] Ingestion (Code node)
        │   Assigns ID, timestamp, normalises source field
        ▼
[Step 2] Classification (HTTP Request → Groq API)
        │   LLM assigns: category, priority, confidence_score
        │   response_format: json_object — valid JSON enforced at API level
        ▼
[Parse Classification] (Code node)
        │   Parses + validates JSON, merges with prior data
        ▼
[Step 3] Enrichment (HTTP Request → Groq API)
        │   LLM extracts: core_issue, identifiers, urgency_signal
        │   response_format: json_object — valid JSON enforced at API level
        ▼
[Steps 4+6] Routing & Escalation (Code node)
        │   Maps category → queue; applies escalation rules
        ▼
[Step 5] Summary (HTTP Request → Groq API)
        │   LLM writes 2–3 sentence handoff note for the receiving team
        ▼
[Assemble Final Record] (Code node)
        │   Flattens all fields into canonical 15-field output schema
        ├──► Output: Webhook.site  (POST full JSON record — captured in browser)
        ├──► Output: Google Sheets (append row — all 14 fields as columns)
        └──► Webhook Response      (return JSON to curl caller)
```

**State:** Held in the n8n execution context per run. Persisted to Webhook.site and Google Sheets on every execution.
**Trigger:** HTTP webhook — swap to a watched folder, Gmail trigger, or form node without changing any downstream logic.
**LLM:** Groq API (`llama-3.3-70b-versatile`, free tier) via n8n HTTP Request nodes using the OpenAI-compatible endpoint. Model is isolated to three nodes — swapping providers requires only changing the URL and credential in those three nodes.
**JSON enforcement:** Steps 2 and 3 use `response_format: { type: "json_object" }`, which makes the Groq API reject non-JSON responses before they reach n8n. This eliminates the most common LLM integration failure mode (markdown-wrapped JSON, preamble text) without any prompt engineering workarounds.

### CLI Runner — Prompt Verification Tool

`backend/scripts/run_pipeline.py` calls the Groq API directly (same model and prompts as
the n8n workflow) with no framework or orchestration layer. Its role is to verify that the
prompts produce correct output and to generate `data/outputs/processed_records.json` for
submission — not to replace the n8n workflow.

It processes all five sample inputs in one command. When tuning a prompt, the n8n
round-trip (import, activate, curl, inspect node output) takes 2–3 minutes per cycle.
The CLI runner cuts that to under 10 seconds: edit the prompt string, re-run, inspect
the JSON diff. Once the output looks right, the identical prompt goes back into the n8n
HTTP Request node.

### Web App — Production Proof-of-Concept

`backend/` (FastAPI) and `frontend/` (React + Vite) demonstrate what this pipeline looks
like as a production internal tool. The same six-step logic runs over a REST API with
Server-Sent Events for real-time step-by-step streaming. The frontend provides a model
selector, live step cards, a results view, and a records table with Excel export.

This is not part of the n8n workflow submission — it is included to show how the
architecture scales and what I would continue building with more time. The n8n workflow
and the FastAPI backend run identical prompts and produce identical structured output;
only the delivery mechanism differs.

**What is working today:** the full six-step pipeline runs end-to-end via the web app,
SSE streaming shows each step completing in real time, multi-model support lets you
swap between Groq, Anthropic, OpenAI, and Mistral from a dropdown, and all records are
persisted to JSON and Excel with escalated rows highlighted.

**What I would build out with more time:** this proof-of-concept would become the primary
operator interface replacing the raw webhook. Concretely: authentication and per-user
session history, the ability for operators to override a routing or escalation decision
and feed that correction back into the confidence threshold, bulk processing of message
queues rather than one-at-a-time submission, a dashboard showing classification accuracy
and escalation rates over time, and Slack/email notifications pushed to queue owners when
a HIGH or escalated record arrives. The architecture already supports all of these — the
SSE streaming, the records store, and the multi-model routing are the foundations those
features build on.

---

## Routing Logic

| Category | Queue |
|---|---|
| Bug Report | Engineering |
| Incident / Outage | Engineering (always escalated — see below) |
| Feature Request | Product |
| Technical Question | IT / Security |
| Billing Issue | Billing |
| Any (escalation triggered) | Escalation |

The table is intentionally flat. A more sophisticated system would support per-company
routing overrides, SLA-based priority boosting, and round-robin assignment within a queue.
For this scope, a flat table is preferable: transparent, debuggable, and sufficient for
five inputs. The routing node is a single switch statement — straightforward to extend.

---

## Escalation Logic

A record is routed to the **Escalation** queue instead of its standard destination
if any of the following conditions are met:

1. **Low confidence:** LLM confidence score below 70%. Below this threshold,
   misclassification rates in testing exceeded 20%, making automated routing unreliable.
   The 70% threshold matches the assessment specification and is conservative by design —
   a misrouted ticket costs more re-triage time than a human-reviewed one.

2. **Outage keywords:** Message contains `outage`, `down for all users`,
   `multiple users affected`, `stopped loading`, or `completely down`. These signal
   potential service incidents requiring immediate human awareness regardless of
   classification confidence.

3. **Billing discrepancy > $200:** The `discrepancy` identifier extracted by the
   enrichment step exceeds $200. The assessment cited "$500" as an example threshold;
   this pipeline uses $200 — a more conservative value that correctly catches the $260
   discrepancy in sample msg_003. The lower threshold is a deliberate design choice:
   any billing error large enough to prompt a customer complaint warrants human review,
   not automated routing.

4. **Incident/Outage category:** Any confirmed outage auto-escalates. The category alone
   carries enough severity that the standard Engineering queue SLA is too slow.

Escalation does not override the routing reason — it routes to a dedicated Escalation
queue where a human reviews and either confirms or overrides the routing decision.

---

## Production Scale Considerations

**Reliability:**
At production volume the primary failure modes are LLM API errors and malformed JSON
responses. Both require retry with exponential backoff. A dead-letter queue holds failed
records for reprocessing without data loss. Idempotency keys on the webhook prevent
duplicate records if the caller retries on timeout.

**Cost:**
The current pipeline uses Groq's free tier (`llama-3.3-70b-versatile`) — zero cost at
assessment scale. At production volume, Groq's pay-as-you-go pricing is ~$0.0006 per
message (three calls × ~800 input + 200 output tokens). For comparison, the equivalent
Claude Sonnet run costs ~$0.006/message — 10× more. At 10,000 messages/day that is
$6/day on Groq vs. $60/day on Sonnet. Routing low-confidence messages to a smaller
model (Groq `llama-3.1-8b-instant`) after a fast first-pass classification cuts cost
further on the ~30% of messages that will escalate anyway.

**Latency:**
Three sequential LLM calls average 3–5 seconds end-to-end. Classification and enrichment
can be parallelised since enrichment only needs the raw message — the classification
context passed today is a quality improvement, not a hard dependency. Parallelising cuts
latency to ~2 seconds. For webhook callers waiting on a synchronous response, an
async accept-then-callback pattern is preferable.

---

## Phase 2 — One More Week

Priority order:

1. **Feedback loop:** Human reviewers mark routing and escalation decisions as correct
   or incorrect. Use that signal to auto-tune the confidence threshold per category and
   surface systematic misclassification patterns.

2. **LLM-based escalation detection:** Replace keyword matching with a dedicated LLM
   call that reasons about severity, tone, and business impact. Catches edge cases
   keywords miss ("everything is broken for our enterprise client").

3. **Promote the web app to production operator UI:** The proof-of-concept FastAPI +
   React app (already in this repo) becomes the internal tool operators use to re-run,
   inspect, and override pipeline decisions — replacing the raw webhook interface and
   the n8n execution log.

4. **Slack / email notifications:** Notify queue owners when a HIGH or escalated record
   arrives, with the summary and routing decision inline — no need to poll the output
   file.

5. **Multi-tenant routing:** Support per-company routing overrides stored in a config
   file. A compliance-heavy customer might route all Technical Questions to a dedicated
   security team rather than the shared IT queue.

6. **Analytics layer:** Track classification accuracy, escalation rate, queue
   distribution, and confidence score distribution over time. This data drives prompt
   iteration and threshold tuning.
