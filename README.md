# ArcVault Intake & Triage Pipeline

> AI Engineer Technical Assessment — Valsoft Corporation | February 2026

An AI-powered intake, classification, enrichment, and routing pipeline for unstructured
B2B customer support messages. Three ways to run it: n8n workflow, FastAPI web app, or Python CLI.

---

## Quick Start

### Option A — n8n (recommended for demo)

```bash
n8n import:workflow --input=n8n/workflow.json
n8n start
```

Open http://localhost:5678, add your Anthropic API key credential (see [n8n/README.md](./n8n/README.md)), activate the workflow, then test with:

```bash
curl -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Web Form","raw_message":"Dashboard stopped loading. Multiple users affected."}'
```

→ See [n8n/README.md](./n8n/README.md) for the full setup guide, credential config, all 5 curl commands, and demo script.

---

### Option B — Web App (FastAPI + React)

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — pick a model, paste a message, watch each step run live.

→ See [backend/README.md](./backend/README.md) and [frontend/README.md](./frontend/README.md).

---

### Option C — Python CLI

Fastest way to generate the assessment output file (`data/outputs/processed_records.json`).
No FastAPI or n8n required — uses the Anthropic SDK directly.

```bash
cp .env.example .env   # add ANTHROPIC_API_KEY
pip install anthropic python-dotenv
python backend/scripts/run_pipeline.py        # processes all 5 sample inputs
python backend/scripts/validate_outputs.py   # validates output schema
```

---

## Pipeline Steps

```
POST /webhook/arcvault-intake  (n8n)
POST /api/run                  (FastAPI, SSE streaming)
              │
              ▼
[1] Ingestion ──────────── Assigns ID + timestamp, normalises source
              │
              ▼
[2] Classification ─────── LLM → category, priority, confidence_score
              │
              ▼
[3] Enrichment ──────────── LLM → core_issue, identifiers, urgency_signal
              │
              ▼
[4+6] Routing & Escalation ─ Maps category → queue; applies escalation rules
              │
              ├─ confidence ≥ 70% + no keywords → Standard queue
              └─ confidence < 70% OR keywords OR Incident → Escalation queue
              │
              ▼
[5] Summary ─────────────── LLM → 2–3 sentence handoff note for receiving team
              │
              ▼
Output: JSON record + row in Excel file
```

---

## Routing Table

| Category | Queue |
|---|---|
| Bug Report | Engineering |
| Incident / Outage | Engineering (always escalated) |
| Feature Request | Product |
| Technical Question | IT / Security |
| Billing Issue | Billing |
| Low Confidence (< 70%) | Escalation |

---

## Escalation Rules

A record is flagged and routed to **Escalation** if any condition is met:

1. LLM confidence **< 70%**
2. Message contains: `outage`, `down for all users`, `multiple users affected`, `stopped loading`, `completely down`
3. Extracted billing discrepancy **> $200**
4. Category is **Incident / Outage** (always auto-escalates)

---

## Multi-Model Support

The web app and CLI both support switching between LLM providers.
Add the relevant key to `.env` — only configured providers appear in the model dropdown.

| Provider | Env var |
|---|---|
| Anthropic (Claude) | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Groq | `GROQ_API_KEY` |
| Mistral | `MISTRAL_API_KEY` |
| Ollama (local) | *(no key needed)* |

---

## Repository Layout

```
arcvault-intake-triage-pipeline/
├── backend/          ← FastAPI + LiteLLM + storage + tests
├── frontend/         ← React + Vite + Tailwind
├── n8n/              ← workflow.json + full setup guide
├── data/
│   ├── sample_inputs.json          ← 5 assessment test messages
│   └── outputs/                    ← generated (gitignored)
│       ├── processed_records.json
│       └── processed_records.xlsx
├── prompts/          ← LLM prompt docs with rationale
├── docs/             ← architecture write-up
└── .env.example      ← all required env vars
```

---

## Deliverables Index

| Deliverable | Location |
|---|---|
| Working workflow (n8n) | `n8n/workflow.json` |
| n8n setup + demo guide | `n8n/README.md` |
| Web app backend | `backend/` |
| Web app frontend | `frontend/` |
| Structured output (5 inputs) | `data/outputs/processed_records.json` *(run CLI to generate)* |
| Classification prompt + rationale | `prompts/classification_prompt.md` |
| Enrichment prompt + rationale | `prompts/enrichment_prompt.md` |
| Summary prompt + rationale | `prompts/summary_prompt.md` |
| Architecture write-up | `docs/architecture.md` |

---
