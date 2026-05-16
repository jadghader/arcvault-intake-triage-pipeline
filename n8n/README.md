# n8n — Self-Hosted Workflow

The ArcVault pipeline runs end-to-end in n8n as a webhook-triggered workflow.
This is the primary demo path for the assessment.

---

## Prerequisites

n8n installed globally via npm:
```bash
npm install -g n8n
```

---

## First-Time Setup (run once)

### 1. Import the workflow
```bash
# From the repo root
n8n import:workflow --input=n8n/workflow.json
```

### 2. Start n8n
```bash
n8n start
```
Open **http://localhost:5678** in your browser.

### 3. Add your Anthropic API key (credential)

This is the only manual step required before the workflow can run.

1. In the n8n sidebar, go to **Credentials** → **Add Credential**
2. Search for **"HTTP Header Auth"** and select it
3. Fill in:
   - **Name:** `Anthropic API`
   - **Name (header):** `x-api-key`
   - **Value:** your `ANTHROPIC_API_KEY` (starts with `sk-ant-`)
4. Click **Save**

### 4. Apply the credential to the workflow

1. Open **Workflows** → **ArcVault Intake & Triage Pipeline**
2. Click the **Step 2: Classification (LLM)** node
3. Under **Authentication** → **Credential for HTTP Header Auth** → select `Anthropic API`
4. Repeat for **Step 3: Enrichment (LLM)** and **Step 5: Summary (LLM)**
5. Click **Save** (top-right)

### 5. Activate the workflow

Toggle the **Inactive** switch in the top-right to **Active**.
The webhook URL is now live at `http://localhost:5678/webhook/arcvault-intake`.

---

## Workflow Overview

The workflow has 8 nodes wired in a linear chain:

```
Webhook Trigger
    │  POST /webhook/arcvault-intake
    ▼
Step 1: Ingestion  (Code node)
    │  Normalises input: assigns ID, timestamp, source
    ▼
Step 2: Classification  (HTTP Request → Anthropic API)
    │  LLM assigns: category, priority, confidence_score
    ▼
Parse Classification  (Code node)
    │  Parses JSON response, validates category/priority, merges with prev data
    ▼
Step 3: Enrichment  (HTTP Request → Anthropic API)
    │  LLM extracts: core_issue, identifiers, urgency_signal
    ▼
Steps 4+6: Routing & Escalation  (Code node)
    │  Routing table maps category → queue
    │  Escalation triggers: confidence < 70%, keywords, billing discrepancy, Incident category
    ▼
Step 5: Summary  (HTTP Request → Anthropic API)
    │  LLM writes 2–3 sentence handoff note for receiving team
    ▼
Assemble Final Record  (Code node)
    │  Combines all fields into one clean JSON record
    ▼
Webhook Response
    └  Returns the full structured record as JSON to the caller
```

### Escalation Rules (in the workflow code)

A record is routed to the **Escalation** queue instead of the standard destination if any of:
- Confidence score **< 70%**
- Message contains: `outage`, `down for all users`, `multiple users affected`, `stopped loading`, `completely down`
- Billing `discrepancy` identifier extracted with value **> $200**
- Category is **Incident / Outage** (always escalates)

---

## Running the Demo

### Option A — curl (one message at a time)

```bash
# msg_001 — Bug Report / Auth error → Engineering
curl -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Email","raw_message":"Hi, I tried logging in this morning and keep getting a 403 error. My account is arcvault.io/user/jsmith. This started after your update last Tuesday."}'

# msg_002 — Feature Request → Product
curl -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Web Form","raw_message":"We'\''d love to see a bulk export feature for our audit logs. We'\''re a compliance-heavy org and this would save us hours every month."}'

# msg_003 — Billing Issue / $260 discrepancy → ESCALATION
curl -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Support Portal","raw_message":"Invoice #8821 shows a charge of $1,240 but our contract rate is $980/month. Can someone look into this?"}'

# msg_004 — Technical Question / SSO → IT / Security
curl -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Email","raw_message":"I'\''m not sure if this is the right place to ask, but is there a way to set up SSO with Okta? We'\''re evaluating switching our auth provider."}'

# msg_005 — Incident / Multiple users → ESCALATION
curl -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Web Form","raw_message":"Your dashboard stopped loading for us around 2pm EST. Checked our end — it'\''s definitely on yours. Multiple users affected."}'
```

### Option B — Python CLI (all 5 at once)

This bypasses n8n and calls the Anthropic API directly. Good for generating the assessment output file.

```bash
# From repo root
cp .env.example .env       # add ANTHROPIC_API_KEY
pip install anthropic python-dotenv
python scripts/run_pipeline.py
# Writes data/outputs/processed_records.json
```

---

## Expected Outputs

| Message | Category | Queue | Escalated |
|---|---|---|---|
| msg_001 (403 error) | Bug Report | Engineering | No |
| msg_002 (bulk export) | Feature Request | Product | No |
| msg_003 (invoice $260 over) | Billing Issue | Escalation | **Yes** — discrepancy > $200 |
| msg_004 (Okta SSO) | Technical Question | IT / Security | No |
| msg_005 (outage, multiple users) | Incident / Outage | Escalation | **Yes** — keyword + category |

---

## Viewing Execution Results in n8n

After sending a curl request:
1. In n8n, click **Executions** (left sidebar)
2. Click the latest execution to open it
3. Click any node to see its input and output data
4. The **Assemble Final Record** node shows the complete structured output
5. The **Steps 4+6** node shows the routing decision and escalation flag

---

## Suggested Demo Script (for recording)

1. Show the workflow canvas — walk through each node from left to right (30 sec)
2. Send `msg_003` (billing) — highlight escalation in execution log (1 min)
3. Send `msg_005` (outage) — show keyword-triggered escalation (1 min)
4. Send `msg_002` (feature request) — show clean non-escalated routing to Product (30 sec)
5. Show **Executions** list with all 5 runs completed (30 sec)

---

## Stop n8n

`Ctrl+C` in the terminal running `n8n start`.

Workflows and credentials persist in `~/.n8n` between restarts.
