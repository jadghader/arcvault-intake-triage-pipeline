# CLAUDE.md — ArcVault Intake & Triage Pipeline

> Primary context document for Claude Code sessions.
> Read this first before making any changes to this repo.

---

## Project Overview

**Repo:** `arcvault-intake-triage-pipeline`
**Purpose:** AI-powered intake and triage pipeline for a synthetic B2B SaaS company called "ArcVault." Ingests unstructured customer messages, classifies them via LLM, enriches them with structured entities, routes them to the correct queue, and flags escalations for human review.

**Component roles:**
- **n8n workflow** — primary assessment deliverable. All six pipeline steps run inside n8n, triggered by HTTP webhook. Evaluators start here.
- **Python CLI** (`backend/scripts/run_pipeline.py`) — calls Groq API directly (same model/prompts as n8n) to verify prompt outputs and generate `data/outputs/processed_records.json`. Not a replacement for n8n.
- **FastAPI + React web app** — proof-of-concept showing how this design scales to production. Same six-step pipeline over a REST API with SSE streaming and a React operator UI.

---

## Monorepo Structure

```
arcvault-intake-triage-pipeline/
├── backend/                    ← FastAPI + OpenAI Agents SDK (Python)
│   ├── app/
│   │   ├── main.py             ← FastAPI app entry point
│   │   ├── config.py           ← Settings + model registry + env setup
│   │   ├── pipeline/           ← classification, enrichment, routing, escalation, summary, runner
│   │   ├── storage/            ← json_store.py + excel_store.py
│   │   ├── schemas/            ← Pydantic models (pipeline.py)
│   │   └── routers/            ← /api/run, /api/records, /api/models
│   ├── scripts/
│   │   ├── run_pipeline.py     ← CLI runner (Groq via OpenAI SDK, no FastAPI needed)
│   │   └── validate_outputs.py ← output schema validator for submission
│   ├── tests/                  ← pytest (routing, escalation, API) — 21 tests, no LLM calls
│   └── requirements.txt
├── frontend/                   ← React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── hooks/usePipelineRun.ts  ← SSE consumer
│       ├── components/              ← ModelSelector, StepProgress, ResultCard, RecordsTable
│       ├── pages/                   ← PipelinePage, RecordsPage
│       └── App.tsx
├── n8n/
│   ├── workflow.json           ← importable n8n workflow (primary deliverable)
│   └── README.md               ← full setup, credential config, curl commands, demo script
├── data/
│   ├── sample_inputs.json      ← 5 assessment test messages
│   └── outputs/                ← processed_records.json + .xlsx (generated, gitignored)
├── prompts/                    ← all 3 LLM prompt docs with rationale
└── docs/
    └── architecture.md         ← system design, routing, escalation, prod scale, Phase 2
```

---

## Architecture

```
POST /webhook/arcvault-intake  (n8n — primary)
POST /api/run                  (FastAPI — proof-of-concept)
              │
              ▼
[1] Ingestion ──────────── Assigns ID + timestamp, normalises source
              │
              ▼
[2] Classification ─────── LLM → category, priority, confidence_score
              │             JSON schema enforced via response_format (n8n) / Pydantic output_type (FastAPI)
              ▼
[3] Enrichment ──────────── LLM → core_issue, identifiers, urgency_signal
              │             JSON schema enforced same way
              ▼
[4+6] Routing & Escalation ─ Pure Python: maps category → queue, applies escalation rules
              │
              ├─ confidence ≥ 70% + no keywords + no billing trigger → Standard queue
              └─ confidence < 70% OR outage keywords OR discrepancy > $200 OR Incident → Escalation
              │
              ▼
[5] Summary ─────────────── LLM → 2–3 sentence handoff note
              │
              ▼
Output: flat 15-field JSON record
```

**LLM (n8n + CLI):** Groq `llama-3.3-70b-versatile` (free tier) via OpenAI-compatible endpoint.
**LLM (FastAPI web app):** Multi-model via OpenAI Agents SDK — Anthropic, OpenAI, Groq, Mistral, Ollama.
**JSON enforcement (n8n):** `response_format: { type: "json_object" }` at API level on Steps 2 + 3.
**JSON enforcement (FastAPI):** Pydantic `output_type` on each Agent — schema derived from model, enforced by SDK.

---

## Output Schema (15 fields)

```json
{
  "id": "msg_001",
  "source": "Web Form",
  "timestamp": "2026-05-17T11:11:36Z",
  "raw_message": "...",
  "category": "Billing Issue",
  "priority": "High",
  "confidence_score": 0.98,
  "core_issue": "...",
  "identifiers": { "invoice_number": "8821", "discrepancy": "260" },
  "urgency_signal": "...",
  "destination_queue": "Escalation",
  "routing_reason": "Billing discrepancy $260 exceeds $200 threshold",
  "escalation_flag": true,
  "escalation_reason": "Billing discrepancy $260 exceeds $200 threshold",
  "summary": "..."
}
```

---

## Routing Logic

| Category | Queue |
|---|---|
| Bug Report | Engineering |
| Incident / Outage | Engineering (always escalated) |
| Feature Request | Product |
| Technical Question | IT / Security |
| Billing Issue | Billing |

---

## Escalation Rules

A record routes to **Escalation** if any condition is met:

1. `confidence_score < 0.70`
2. Message contains: `outage`, `down for all users`, `multiple users affected`, `stopped loading`, `completely down`
3. Extracted `discrepancy` identifier > $200
4. Category is `Incident / Outage` (always escalates regardless of confidence)

---

## Key Design Decisions

**$200 billing threshold (not $500):** The assessment cited $500 as an example. $200 is more conservative and correctly catches the $260 discrepancy in sample msg_003. Documented in `docs/architecture.md`.

**Groq free tier for n8n:** Removes the biggest setup barrier for evaluators. `llama-3.3-70b-versatile` supports `response_format: json_object` which is the critical capability.

**`response_format: json_object` on Steps 2+3:** Eliminates the #1 LLM integration failure mode (markdown-wrapped JSON, preamble text) without prompt engineering workarounds. Step 5 (summary) intentionally does NOT use it — plain text output.

**OpenAI Agents SDK for FastAPI (not LiteLLM):** One agent per LLM step with Pydantic `output_type` gives structured output enforcement at the schema level, not just prompt level. Agents created per-request via `_make_agent(model)` factory so the model string can vary at call time.

**Chained prompts (not one mega-prompt):** Classification → Enrichment → Summary are separate calls. Easier to debug, tune, and swap independently. Classification context is passed into Enrichment so the model knows which identifiers to prioritise.

**Dynamic `identifiers` object:** Messages vary — some have invoice numbers, some have error codes, some have neither. A fixed nullable schema produces noisy output. A dynamic key-value object with a controlled vocabulary produces only what is present.

**SSE from POST (not WebSocket):** Simpler, no persistent connection management, works well for request-response with streaming.

---

## Running the Project

### n8n (primary)
```bash
n8n import:workflow --input=n8n/workflow.json
n8n start
# Open http://localhost:5678, add Groq credential, activate, then:
curl -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Web Form","raw_message":"Your dashboard stopped loading. Multiple users affected."}'
```
Full guide with all 5 curl commands → `n8n/README.md`

### Python CLI (verification)
```bash
cp backend/.env.example .env   # fill in GROQ_API_KEY
pip install openai python-dotenv
python backend/scripts/run_pipeline.py        # generates data/outputs/processed_records.json
python backend/scripts/validate_outputs.py   # validates schema
```

### FastAPI + React (proof-of-concept)
```bash
# Terminal 1
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm install && npm run dev
# Open http://localhost:5173
```

### Tests
```bash
cd backend && pytest
# 21 tests — routing, escalation, API endpoints. No LLM calls.
```

---

## Environment Variables

| Variable | Component | Description |
|---|---|---|
| `GROQ_API_KEY` | n8n + CLI | Groq API key — free tier at console.groq.com |
| `ANTHROPIC_API_KEY` | Web app (optional) | Anthropic key for FastAPI multi-model |
| `OPENAI_API_KEY` | Web app (optional) | OpenAI key for FastAPI multi-model |
| `MISTRAL_API_KEY` | Web app (optional) | Mistral key for FastAPI multi-model |
| `WEBHOOK_SITE_URL` | n8n | Unique URL from webhook.site |
| `GOOGLE_SHEET_ID` | n8n | Sheet ID from Google Sheets URL |
| `OUTPUT_DIR` | CLI + web app | Output directory (default: `data/outputs`) |

See `n8n/.env.example` and `backend/.env.example` for full examples.

---

## Deliverables

| Deliverable | Location |
|---|---|
| Working n8n workflow | `n8n/workflow.json` |
| n8n setup + demo guide | `n8n/README.md` |
| Structured output (5 inputs) | `data/outputs/processed_records.json` *(run CLI to generate)* |
| Classification prompt + rationale | `prompts/classification_prompt.md` |
| Enrichment prompt + rationale | `prompts/enrichment_prompt.md` |
| Summary prompt + rationale | `prompts/summary_prompt.md` |
| Architecture write-up | `docs/architecture.md` |
| FastAPI backend (proof-of-concept) | `backend/` |
| React frontend (proof-of-concept) | `frontend/` |
