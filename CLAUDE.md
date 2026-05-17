# CLAUDE.md — ArcVault Intake & Triage Pipeline

> This file is the primary context document for Claude Code and Claude chat sessions.
> It contains the full project purpose, architecture decisions, prompt history, and
> instructions for continuing work on this repo. Keep it updated as the project evolves.

---

## Project Overview

**Repo:** `arcvault-intake-triage-pipeline`
**Status:** Full-stack monorepo — n8n workflow (primary), Python CLI (verification), FastAPI + React (production proof-of-concept).

This repo implements an AI-powered intake and triage pipeline for a synthetic B2B SaaS company
called "ArcVault." The pipeline ingests unstructured customer messages, classifies them via LLM,
enriches them with structured entities, routes them to the correct queue, and flags escalations
for human review.

**Role of each component:**
- **n8n workflow** — the assessment deliverable. All six pipeline steps run inside n8n, triggered by HTTP webhook. This is what the evaluator should see and run first.
- **Python CLI** (`backend/scripts/run_pipeline.py`) — calls the Anthropic API directly to verify prompt outputs and generate `data/outputs/processed_records.json` for submission. Not a replacement for n8n — a verification and iteration tool.
- **FastAPI + React web app** — proof-of-concept showing how this design scales to production. The same six-step pipeline runs over a REST API with SSE streaming and a React operator UI. Not the primary deliverable; included to demonstrate production-readiness thinking.

---

## Monorepo Structure

```
arcvault-intake-triage-pipeline/
├── backend/                    ← FastAPI + LiteLLM (Python)
│   ├── app/
│   │   ├── main.py             ← FastAPI app entry point
│   │   ├── config.py           ← Settings + LiteLLM model registry
│   │   ├── pipeline/           ← classification, enrichment, routing, escalation, summary, runner
│   │   ├── storage/            ← json_store.py + excel_store.py
│   │   ├── schemas/            ← Pydantic models (pipeline.py)
│   │   └── routers/            ← /api/run, /api/records, /api/models
│   ├── scripts/
│   │   ├── run_pipeline.py     ← CLI runner (Anthropic SDK only, no FastAPI needed)
│   │   └── validate_outputs.py ← output schema validator for submission
│   ├── tests/                  ← pytest (routing, escalation, API)
│   └── requirements.txt
├── frontend/                   ← React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── hooks/usePipelineRun.ts  ← SSE consumer
│       ├── components/              ← ModelSelector, StepProgress, ResultCard, RecordsTable
│       ├── pages/                   ← PipelinePage, RecordsPage
│       └── App.tsx
├── n8n/
│   ├── workflow.json           ← importable n8n workflow
│   └── README.md               ← full setup, credential config, demo script
├── data/
│   ├── sample_inputs.json
│   └── outputs/                ← processed_records.json + .xlsx (generated, gitignored)
├── prompts/                    ← LLM prompt documentation
└── docs/
    └── architecture.md         ← full write-up: all 3 system options, routing, escalation, prod scale
```

## Running the Project

### 1 — n8n Workflow (Primary — start here)
```bash
n8n import:workflow --input=n8n/workflow.json
n8n start
```
Open http://localhost:5678, add Anthropic API key credential (see n8n/README.md), activate workflow.
Full guide with all 5 curl commands and demo script → `n8n/README.md`.

### 2 — Python CLI (Verification / Output Generation)
```bash
cp backend/.env.example .env   # fill in GROQ_API_KEY or ANTHROPIC_API_KEY
pip install anthropic python-dotenv
python backend/scripts/run_pipeline.py        # generates data/outputs/processed_records.json
python backend/scripts/validate_outputs.py   # validates output schema for submission
```

### 3 — FastAPI Backend (Proof-of-Concept)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp backend/.env.example .env   # fill in at least one LLM key
uvicorn app.main:app --reload --port 8000
```
API available at http://localhost:8000. Docs at http://localhost:8000/docs.

### 4 — React Frontend (Proof-of-Concept)
```bash
cd frontend
npm install
npm run dev
```
UI available at http://localhost:5173 (proxies `/api` to backend :8000).

### 5 — Tests
```bash
cd backend
pytest
```

---

## Architecture Summary

```
Inbound Message (webhook / folder watch / form)
        │
        ▼
[Step 1] Ingestion Node
        │   Accepts raw message + metadata (source, timestamp)
        ▼
[Step 2] Classification Node  ──► LLM (claude-sonnet-4-20250514 via Anthropic API)
        │   Assigns: Category, Priority, Confidence Score
        ▼
[Step 3] Enrichment Node  ──────► LLM (same model, chained prompt)
        │   Extracts: core_issue, identifiers, urgency_signal
        ▼
[Step 4] Routing Decision Node
        │   Maps classification → destination queue
        │   Fallback: low_confidence → escalation queue
        ▼
[Step 5] Structured Output Node
        │   Writes JSON record to outputs/processed_records.json
        │   (+ optional Google Sheet / Webhook.site)
        ▼
[Step 6] Escalation Flag Node
        │   Triggers if: confidence < 70% OR escalation keywords matched
        └──► Routes to escalation_queue instead of standard destination
```

**State:** Held in n8n execution context per run. JSON output written by CLI runner to `data/outputs/processed_records.json`.
**Orchestration:** n8n (self-hosted) — `n8n/workflow.json`
**LLM:** Anthropic API (`claude-sonnet-4-6`) via HTTP Request nodes in n8n; same model used by CLI runner and FastAPI backend.
**Trigger:** HTTP webhook (POST to `/webhook/arcvault-intake`) — swap to watched folder, Gmail trigger, or form node without changing downstream logic.

---

## Routing Logic

| Category | Destination Queue |
|---|---|
| Bug Report | Engineering |
| Incident / Outage | Engineering (HIGH priority auto-escalation) |
| Feature Request | Product |
| Technical Question | IT / Security |
| Billing Issue | Billing |
| Low Confidence (< 70%) | Escalation Queue (human review) |

Escalation override keywords (checked before routing):
- `outage`, `down for all users`, `multiple users affected`, `stopped loading`, `completely down`
- Any billing discrepancy > $200 (extracted by enrichment step)
- Confidence score < 70%
- Category is Incident / Outage (always escalates regardless of confidence)

---

## File Structure

Key locations:
- `n8n/workflow.json` — importable n8n workflow (primary assessment deliverable)
- `n8n/README.md` — full n8n setup, credential config, all 5 curl commands, demo script
- `backend/scripts/run_pipeline.py` — CLI verification runner (Anthropic SDK, no frameworks)
- `backend/scripts/validate_outputs.py` — validates output JSON schema for submission
- `backend/README.md` — FastAPI proof-of-concept: setup, API endpoints, tests
- `frontend/README.md` — React proof-of-concept: setup, component guide, SSE explanation
- `docs/architecture.md` — full write-up: system design, routing, escalation, prod scale, Phase 2
- `data/sample_inputs.json` — 5 test messages from assessment
- `data/outputs/` — generated on CLI run (gitignored): `processed_records.json` + `.xlsx`
- `prompts/` — all 3 LLM prompt docs with rationale paragraphs

---

## Prompt History & Session Log

> Append new sessions below as you work. This gives Claude Code full context when resuming.

### Session 1 — Initial Build
- Created full monorepo structure
- Wrote all 3 LLM prompts (classification, enrichment, summary)
- Implemented n8n workflow JSON covering all 6 steps
- Wrote architecture write-up in `docs/architecture.md`
- Added Python runner as fallback alternative to n8n
- Note: `data/outputs/processed_records.json` was NOT generated — pipeline was never executed

**Decisions made:**
- Chose `claude-sonnet-4-20250514` over GPT-4o: better instruction following for structured JSON output, lower hallucination rate on confidence scores
- Used chained prompts (classification → enrichment) rather than one mega-prompt: easier to debug, swap, or A/B test individual steps
- Stored outputs as append-mode JSON array rather than Google Sheets: portable, version-controllable, no auth required for evaluators
- Escalation threshold set at 70% confidence (per spec) + keyword list derived from assessment's own examples

**What I'd change with more time:**
- Add a feedback loop: human reviewers mark escalations as correct/incorrect → fine-tune confidence thresholds
- Replace keyword matching with a second LLM call for escalation detection
- Add retry logic + dead-letter queue for failed LLM calls

### Session 2 — Requirements Audit (May 2026)
- Audited all deliverables against `AI_Engineer_Technical_Intermediate-Senior.docx`
- Confirmed all 6 workflow steps are correctly implemented in both `n8n_workflow.json` and `run_pipeline.py`
- Found 3 blockers that must be resolved before submission (see below)

**Deliverable status after audit:**

| Deliverable | Requirement | Status |
|---|---|---|
| 4.1 Working Workflow | n8n JSON + screenshots OR Loom OR live demo | ⚠️ n8n JSON exists; screenshots folder empty; Loom placeholder unfilled |
| 4.2 Structured Output File | `processed_records.json` with all 5 records | ❌ File does not exist — pipeline has never been run |
| 4.3 Prompt Documentation | 3 prompts + rationale paragraphs | ✅ All 3 complete |
| 4.4 Architecture Write-Up | System design, routing, escalation, prod scale, Phase 2 | ✅ Complete |

### Session 5 — Cleanup: Scripts Moved, GitHub Removed (May 2026)
- Moved `scripts/run_pipeline.py` and `scripts/validate_outputs.py` → `backend/scripts/`; fixed `BASE_DIR` path (`parent.parent.parent` now correctly resolves to repo root)
- Removed `scripts/` top-level directory (no longer exists)
- Removed `.github/workflows/` entirely — this repo is not a git repo and has no remote; CI adds zero value for a take-home assessment submission
- Rewrote `docs/architecture.md` to reflect the full current system: covers all 3 options (n8n, FastAPI+React, CLI), correct routing table, correct escalation thresholds, production scale, Phase 2
- Updated all path references in `README.md` and `CLAUDE.md` (`scripts/` → `backend/scripts/`)

**Why scripts belong in backend/:**
They are Python, use the same data paths as the backend, and logically belong with the Python layer.
Top-level `scripts/` only made sense when n8n was the only runtime — now that FastAPI is primary, it was noise.

**Why .github was removed:**
No git remote, no push triggers, no CI value. The backend tests can be run locally with `pytest`.
Re-add `.github/` only if the repo is pushed to GitHub and CI is actually desired.

### Session 4 — Documentation Pass (May 2026)
- Answered: scripts are still needed — `run_pipeline.py` generates the assessment output file without starting FastAPI; `validate_outputs.py` checks schema for submission
- Fixed GitHub workflow: was triggering on `data/outputs/**` (gitignored — never ran); replaced with `pytest` on the backend
- Expanded `n8n/README.md`: full credential setup in n8n UI v2.8.4, workflow node map, escalation rules, curl commands for all 5 sample messages, expected outputs table, demo script
- Created `backend/README.md`: setup, all API endpoints with request/response format, multi-model table, storage details, test coverage guide
- Created `frontend/README.md`: setup, both pages described, SSE streaming explained, component tree
- Rewrote `README.md`: removed stale paths (`workflow/`, `demo/`), wrong model ID; unified Quick Start covering all 3 run options
- Fixed stale CLAUDE.md: old File Structure section (referenced removed dirs), wrong escalation threshold ($500 → $200), missing keywords
- n8n workflow already imported and n8n running on :5678 — only remaining manual step is API key credential setup in n8n UI

**What's still needed before submitting:**
1. Add Anthropic API key credential in n8n UI (see `n8n/README.md` step 3)
2. Run `python scripts/run_pipeline.py` to generate `data/outputs/processed_records.json`
3. Start backend + frontend to demo the web app
4. Record Loom walkthrough (see demo script in `n8n/README.md`)

### Session 3 — Full-Stack Monorepo Build (May 2026)
- Reorganized into clean monorepo: `backend/`, `frontend/`, `n8n/`, `data/`, `prompts/`, `scripts/`, `docs/`
- Removed Docker Compose in favour of npm global n8n (already installed v2.8.4)
- Moved `workflow/n8n_workflow.json` → `n8n/workflow.json`
- Built FastAPI backend with LiteLLM multi-model support (Anthropic, OpenAI, Groq, Mistral, Ollama)
- SSE streaming from `POST /api/run` — step-by-step real-time events to frontend
- Dual storage: JSON append (`data/outputs/processed_records.json`) + styled Excel (`processed_records.xlsx`)
- Built React + Vite + Tailwind frontend: model dropdown, real-time step cards, result card, records table with Excel export
- 15 unit tests across routing, escalation, and API endpoints
- Fixed all bugs from Session 2 audit (timestamp KeyError, model ID)

**Key tech decisions:**
- **LiteLLM directly** (not OpenAI Agents SDK): linear pipeline doesn't need agent loops; LiteLLM alone handles 100+ models with a model-string swap
- **SSE from POST** (not WebSocket): simpler, no persistent connection management, works well for request-response with streaming
- **Tailwind + manual components** (not shadcn/ui CLI): avoids CLI dependency, full control, same quality output
- **openpyxl** for Excel: row-level formatting (escalated rows highlighted in amber), frozen header, column widths auto-set

### Session 7 — n8n Workflow Overhaul: Groq + Dual Outputs + JSON Schema Enforcement (May 2026)
- Switched LLM from Anthropic `claude-sonnet-4-6` to Groq `llama-3.3-70b-versatile` (free tier, OpenAI-compatible)
- Added `response_format: { type: "json_object" }` to Steps 2 and 3 — JSON now enforced at API level, not just in prompt
- Added parallel output branches from Assemble Final Record: Webhook.site POST + Google Sheets row append
- Rewrote all 3 HTTP Request node bodies to use `specifyBody: "json"` with proper Groq request format
- Added Groq API credential setup instructions to `n8n/README.md` (HTTP Header Auth: `Authorization: Bearer gsk_...`)
- Added Google Sheets credential + column mapping instructions to `n8n/README.md`
- Added Webhook.site setup instructions to `n8n/README.md`
- Updated `.env.example` with `WEBHOOK_SITE_URL` and `GOOGLE_SHEET_ID`
- Updated `docs/architecture.md`: diagram reflects dual outputs, Groq model, JSON enforcement rationale
- Updated cost section: Groq free tier at assessment scale, $0.0006/msg at production vs $0.006/msg for Sonnet
- Reframed framing across all docs: n8n = primary, CLI = verification, web app = proof-of-concept

**Key decisions:**
- Groq over Anthropic for the n8n workflow: free tier removes the biggest setup barrier for evaluators; `response_format` support is the key capability needed
- `response_format: json_object` for Steps 2+3: eliminates the #1 integration failure mode (LLM wraps JSON in markdown or adds preamble) without any prompt workarounds. Step 5 (summary) intentionally does NOT use it — summary is plain text, not JSON
- Dual outputs (Webhook.site + Google Sheets): assessment explicitly accepts both; running both simultaneously shows completeness
- Google Sheets node uses `defineBelow` column mapping with explicit schema — every field is named, typed, and mapped. No guesswork for the evaluator

---

## Pre-Submission Checklist

**Fixed in earlier sessions:**
- [x] Fix `run_pipeline.py` timestamp KeyError — fixed Session 3
- [x] Update model ID to `claude-sonnet-4-6` — fixed Session 3
- [x] Reframe n8n as primary, CLI as verification, web app as production proof-of-concept — Session 6
- [x] Switch LLM to Groq `llama-3.3-70b-versatile` (free tier) — Session 7
- [x] Add `response_format: json_object` to Steps 2 + 3 (JSON enforced at API level) — Session 7
- [x] Add parallel output branches: Webhook.site + Google Sheets — Session 7
- [x] Update n8n/README.md: Groq credential setup, Google Sheets setup, Webhook.site setup — Session 7

**Still required before submitting:**
- [ ] Get free Groq API key at console.groq.com → add as "Groq API" HTTP Header Auth credential in n8n
- [ ] Apply Groq API credential to Steps 2, 3, 5 nodes in n8n
- [ ] Set up Webhook.site URL → update Output: Webhook.site node URL
- [ ] Set up Google Sheet with 14 column headers → add Google Sheets OAuth2 credential → configure Output: Google Sheets node
- [ ] Activate the workflow → send all 5 curl commands → confirm each returns correct structured JSON
- [ ] Verify records appear in Webhook.site and Google Sheet
- [ ] Run `python backend/scripts/run_pipeline.py` to generate `data/outputs/processed_records.json`
- [ ] Run `python backend/scripts/validate_outputs.py` to confirm all 5 records pass schema validation
- [ ] Record Loom demo: canvas walkthrough + 2 curl calls showing execution log + Webhook.site + Sheets (5–8 min)

**Deliverables checklist (per assessment Section 4):**
- [x] 4.1 Working workflow — `n8n/workflow.json` (exportable + importable)
- [ ] 4.1 Demo recording — Loom or screenshots of n8n execution steps
- [ ] 4.2 Structured output file — `data/outputs/processed_records.json` (run CLI to generate)
- [x] 4.3 Prompt documentation — `prompts/classification_prompt.md`, `prompts/enrichment_prompt.md`, `prompts/summary_prompt.md`
- [x] 4.4 Architecture write-up — `docs/architecture.md`

---

## How to Resume Work with Claude Code

When starting a new Claude Code session on this repo, paste this at the top:

```
Read CLAUDE.md first. This is an AI triage pipeline for technical assessment.
The full architecture, routing logic, prompt decisions, and session history are documented there.
Current task: [describe what you want to do]
```

---

## Environment Variables

See `.env.example` for all required vars. Key ones:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `N8N_WEBHOOK_URL` | Your n8n instance webhook URL |
| `OUTPUT_PATH` | Path to write processed_records.json (default: `data/outputs/`) |
| `ESCALATION_WEBHOOK` | Webhook.site URL for escalation queue |
| `STANDARD_WEBHOOK` | Webhook.site URL for standard routing output |

---

## Running the Pipeline

### Option 1 — n8n (primary)
1. `n8n import:workflow --input=n8n/workflow.json`
2. `n8n start` → open http://localhost:5678
3. Add Anthropic API key credential (see `n8n/README.md` Step 3)
4. Activate workflow → POST to `http://localhost:5678/webhook/arcvault-intake`
5. Full curl commands and demo script in `n8n/README.md`

### Option 2 — Python CLI (verification)
```bash
cp backend/.env.example .env   # fill in GROQ_API_KEY or ANTHROPIC_API_KEY
pip install anthropic python-dotenv
python backend/scripts/run_pipeline.py        # generates data/outputs/processed_records.json
python backend/scripts/validate_outputs.py   # validates schema for submission
```

### Option 3 — Web app (proof-of-concept)
```bash
# Terminal 1
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
# Terminal 2
cd frontend && npm install && npm run dev
# Open http://localhost:5173
```
