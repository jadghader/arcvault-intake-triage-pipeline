# Backend — FastAPI + LiteLLM

The Python backend for the ArcVault pipeline web app.
Exposes a REST API that the React frontend consumes.

---

## Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 |
| Multi-model LLM | LiteLLM 1.55 (Anthropic, OpenAI, Groq, Mistral, Ollama) |
| Storage | JSON append + Excel (openpyxl) |
| Streaming | Server-Sent Events (SSE) from `POST /api/run` |
| Tests | pytest + pytest-asyncio |

---

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the **repo root** (not inside `backend/`):
```bash
cp .env.example .env
# Open .env and add at least one API key:
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Run

```bash
# From inside backend/
uvicorn app.main:app --reload --port 8000
```

- API: **http://localhost:8000**
- Interactive docs: **http://localhost:8000/docs**
- Health check: **http://localhost:8000/health**

---

## API Endpoints

### `POST /api/run`
Submit a message and stream step-by-step pipeline events via SSE.

**Request body:**
```json
{
  "raw_message": "Your dashboard stopped loading. Multiple users affected.",
  "source": "Web Form",
  "model": "claude-sonnet-4-6"
}
```

**Response:** `text/event-stream` — one SSE event per pipeline step:
```
data: {"step": 1, "name": "ingestion", "status": "done", "data": {...}}
data: {"step": 2, "name": "classification", "status": "running", "data": null}
data: {"step": 2, "name": "classification", "status": "done", "data": {"category": "Incident / Outage", ...}}
data: {"step": 3, "name": "enrichment", "status": "running", "data": null}
data: {"step": 3, "name": "enrichment", "status": "done", "data": {...}}
data: {"step": 4, "name": "routing", "status": "done", "data": {"destination_queue": "Escalation", ...}}
data: {"step": 5, "name": "summary", "status": "done", "data": {"summary": "..."}}
data: {"step": 6, "name": "complete", "status": "done", "data": <full ProcessedRecord>}
```

Event `status` values: `running` | `done` | `error`

---

### `GET /api/records`
Returns all processed records as a JSON array.

### `GET /api/records/{id}`
Returns a single record by ID. 404 if not found.

### `GET /api/records/export/excel`
Downloads `data/outputs/processed_records.xlsx`.
Escalated rows are highlighted in amber. Headers are frozen.

### `GET /api/models`
Returns available models grouped by provider (only providers with API keys configured).

**Response:**
```json
{
  "available": {
    "anthropic": ["claude-sonnet-4-6", "claude-haiku-4-5", "claude-opus-4-7"],
    "groq": ["groq/llama-3.3-70b-versatile", ...]
  },
  "default": "claude-sonnet-4-6"
}
```

---

## Multi-Model Support

Models are switched by changing the `model` field in the run request.
LiteLLM handles routing to the correct provider automatically.

Supported providers (add the corresponding key to `.env`):

| Provider | Env var | Example model |
|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-6` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` |
| Groq | `GROQ_API_KEY` | `groq/llama-3.3-70b-versatile` |
| Mistral | `MISTRAL_API_KEY` | `mistral/mistral-large-latest` |
| Ollama (local) | *(none)* | `ollama/llama3.2` |

---

## Storage

Every processed record is written to two files in `data/outputs/`:

| File | Format | Notes |
|---|---|---|
| `processed_records.json` | JSON array | Append-mode; all runs accumulate |
| `processed_records.xlsx` | Excel | Escalated rows highlighted amber; headers frozen |

Both files are gitignored (generated on first run).

---

## Tests

```bash
# From inside backend/
pytest

# With verbose output
pytest -v

# Single file
pytest tests/test_escalation.py -v
```

**Test coverage:**

| File | What it tests |
|---|---|
| `test_routing.py` | All 5 category→queue mappings, escalation override, unknown category fallback |
| `test_escalation.py` | All 4 escalation triggers, threshold boundaries, clean-message pass-through |
| `test_api.py` | Health, models, records endpoints; empty-message 422 validation |

Tests do **not** call the LLM — routing and escalation are pure logic with no external dependencies.

---

## Project Structure

```
backend/
├── app/
│   ├── main.py               ← FastAPI app, CORS, router registration
│   ├── config.py             ← Settings (env vars), model registry, LiteLLM env setup
│   ├── pipeline/
│   │   ├── classification.py ← LiteLLM call → ClassificationResult
│   │   ├── enrichment.py     ← LiteLLM call → EnrichmentResult
│   │   ├── routing.py        ← Pure routing table logic (no LLM)
│   │   ├── escalation.py     ← Pure escalation logic (no LLM)
│   │   ├── summary.py        ← LiteLLM call → summary string
│   │   └── runner.py         ← Orchestrator; yields StepEvent objects (SSE source)
│   ├── storage/
│   │   ├── json_store.py     ← load_records(), append_record()
│   │   └── excel_store.py    ← upsert_record() with formatting
│   ├── schemas/
│   │   └── pipeline.py       ← All Pydantic models (request, results, events)
│   └── routers/
│       ├── pipeline.py       ← POST /api/run (SSE StreamingResponse)
│       ├── records.py        ← GET /api/records, /export/excel, /{id}
│       └── models.py         ← GET /api/models
└── tests/
    ├── conftest.py
    ├── test_routing.py
    ├── test_escalation.py
    └── test_api.py
```
