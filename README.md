# ArcVault Intake & Triage Pipeline

> AI Engineer Technical Assessment 

An AI-powered intake, classification, enrichment, and routing pipeline for unstructured
B2B customer support messages.

**Primary delivery:** n8n webhook workflow (the assessed artifact).
**Verification tool:** Python CLI — runs the same prompts headlessly and writes the output file.
**Production proof-of-concept:** FastAPI + React web app — demonstrates how this system scales beyond n8n.

---

## Option 1 — n8n Workflow (Primary)

This is the workflow the assessment asks for. It runs all six pipeline steps inside n8n,
triggered by HTTP webhook, with each step visible as an inspectable node in the UI.

```bash
n8n import:workflow --input=n8n/workflow.json
n8n start
```

Open **http://localhost:5678**, add your Anthropic API key credential (one-time setup — see [n8n/README.md](./n8n/README.md)), activate the workflow, then test with:

```bash
# msg_005 — Incident / Outage → auto-escalated (keyword + category)
curl -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Web Form","raw_message":"Your dashboard stopped loading for us around 2pm EST. Checked our end — it is definitely on yours. Multiple users affected."}'
```

→ Full setup, all 5 curl commands, expected outputs table, and demo script: [n8n/README.md](./n8n/README.md)

---

## Option 2 — Python CLI (Verification / Fallback)

Calls the Anthropic API directly — no n8n, no FastAPI. Used to verify that the prompts
produce the correct structured output and to generate `data/outputs/processed_records.json`
for submission.

```bash
cp backend/.env.example .env  # then fill in GROQ_API_KEY or ANTHROPIC_API_KEY
pip install anthropic python-dotenv
python backend/scripts/run_pipeline.py        # processes all 5 sample inputs
python backend/scripts/validate_outputs.py   # confirms output schema is correct
```

→ Output written to `data/outputs/processed_records.json` (gitignored — run to generate).

---

## Option 3 — Web App (Production Proof-of-Concept)

FastAPI backend + React frontend demonstrating what this pipeline looks like as a
production internal tool. Not the primary assessment deliverable — included to show
how the n8n workflow design translates to a scalable, operator-facing product.

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp backend/.env.example .env   # fill in at least one LLM key
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — pick a model, paste a message, watch each pipeline step
run live with SSE streaming.

→ See [backend/README.md](./backend/README.md) and [frontend/README.md](./frontend/README.md).

---

## Pipeline Steps

```
POST /webhook/arcvault-intake  (n8n — primary)
POST /api/run                  (FastAPI — proof-of-concept)
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
Output: JSON record (+ Excel row in web app mode)
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
3. Extracted billing discrepancy **> $200** (catches the $260 discrepancy in sample msg_003; assessment cited $500 as an example — $200 is the more conservative threshold)
4. Category is **Incident / Outage** (always auto-escalates regardless of confidence)

---

## Model

**n8n workflow:** Groq `llama-3.3-70b-versatile` — free tier, no credit card needed.
Get an API key at [console.groq.com](https://console.groq.com). Steps 2 and 3 use
`response_format: { type: "json_object" }` to enforce valid JSON at the API level.

**Web app + CLI (multi-model):** Add keys to `.env` — only providers with a key appear in the dropdown.

| Provider | Env var |
|---|---|
| Groq (free) | `GROQ_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Mistral | `MISTRAL_API_KEY` |
| Ollama (local) | *(no key needed)* |

---

## Repository Layout

```
arcvault-intake-triage-pipeline/
├── n8n/
│   ├── workflow.json           ← importable n8n workflow (primary deliverable)
│   ├── README.md               ← full setup, demo script, curl commands
│   └── .env.example            ← n8n env vars (Groq key, Webhook.site, Google Sheet ID)
├── backend/
│   ├── scripts/
│   │   ├── run_pipeline.py     ← CLI runner (verification tool)
│   │   └── validate_outputs.py ← output schema validator
│   ├── app/                    ← FastAPI app (proof-of-concept)
│   ├── tests/                  ← pytest suite
│   └── .env.example            ← backend/CLI env vars (LLM keys, output dir)
├── frontend/                   ← React + Vite + Tailwind (proof-of-concept)
├── data/
│   ├── sample_inputs.json      ← 5 assessment test messages
│   └── outputs/                ← generated (gitignored)
│       ├── processed_records.json
│       └── processed_records.xlsx
├── prompts/                    ← all 3 LLM prompt docs with rationale
├── docs/
│   └── architecture.md         ← system design write-up
└── .env.example                ← index: points to n8n/ and backend/ .env.example files
```

---

## Deliverables Index

| Deliverable | Location |
|---|---|
| Working workflow (n8n JSON) | `n8n/workflow.json` |
| n8n setup + demo guide | `n8n/README.md` |
| Structured output (5 inputs) | `data/outputs/processed_records.json` *(run CLI to generate)* |
| Classification prompt + rationale | `prompts/classification_prompt.md` |
| Enrichment prompt + rationale | `prompts/enrichment_prompt.md` |
| Summary prompt + rationale | `prompts/summary_prompt.md` |
| Architecture write-up | `docs/architecture.md` |
| Web app backend (proof-of-concept) | `backend/` |
| Web app frontend (proof-of-concept) | `frontend/` |

---
