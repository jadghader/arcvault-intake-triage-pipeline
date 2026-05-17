# n8n — ArcVault Intake & Triage Pipeline

The ArcVault pipeline runs end-to-end in n8n as a webhook-triggered workflow.
**This is the primary demo path for the assessment.**

**LLM:** Groq — `llama-3.3-70b-versatile` (free tier, OpenAI-compatible API)
**Outputs:** Webhook response (JSON) + Webhook.site capture + Google Sheets row — all three per message.

---

## Prerequisites

```bash
npm install -g n8n          # n8n v2.8+ recommended
```

Get a **free Groq API key** at [console.groq.com](https://console.groq.com) — no credit card required.

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

Open **http://localhost:5678**

---

### 3. Add Groq API credential

The three LLM nodes (Classification, Enrichment, Summary) all call the Groq API using
an HTTP Header Auth credential.

1. Sidebar → **Credentials** → **Add Credential**
2. Search **"HTTP Header Auth"** → select it
3. Fill in:
   - **Name:** `Groq API`
   - **Name (header):** `Authorization`
   - **Value:** `Bearer YOUR_GROQ_API_KEY` *(paste your full key including the `gsk_…` prefix)*
4. **Save**

---

### 4. Apply the credential to the three LLM nodes

1. Open **Workflows** → **ArcVault Intake & Triage Pipeline**
2. Click **Step 2: Classification (LLM)** → under **Authentication** → **Credential for HTTP Header Auth** → select `Groq API`
3. Repeat for **Step 3: Enrichment (LLM)** and **Step 5: Summary (LLM)**
4. **Save** (top-right)

---

### 5. Add Google Sheets credential (for the Sheets output node)

1. Sidebar → **Credentials** → **Add Credential**
2. Search **"Google Sheets OAuth2 API"** → select it
3. Follow the OAuth flow (Google account that owns the target sheet)
4. Open the **Output: Google Sheets** node
5. Set **Credential** → your new Google Sheets credential
6. Set **Document ID** → paste the ID from your sheet URL: `https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit`
7. Set **Sheet Name** → `Sheet1` (or whatever your tab is named)
8. Make sure your sheet has these column headers in row 1:
   `id | source | timestamp | raw_message | category | priority | confidence_score | core_issue | identifiers | urgency_signal | destination_queue | escalation_flag | escalation_reason | summary`
9. **Save**

> **If you skip Google Sheets:** disable the **Output: Google Sheets** node (right-click → Disable). The workflow still runs fully — Webhook.site and the webhook response are unaffected.

---

### 6. Set up Webhook.site

1. Open [webhook.site](https://webhook.site) in your browser — you get a unique URL instantly, no account needed
2. Copy your unique URL (looks like `https://webhook.site/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
3. In n8n: open the **Output: Webhook.site** node → update the URL field with your unique URL
4. **Save**

> Alternatively, set the env var `WEBHOOK_SITE_URL=https://webhook.site/your-uuid` before starting n8n and the node picks it up automatically.

---

### 7. Activate the workflow

Toggle **Inactive → Active** in the top-right of the workflow canvas.

The webhook is now live at: `http://localhost:5678/webhook/arcvault-intake`

---

## Workflow Overview

```
Webhook Trigger
    │  POST /webhook/arcvault-intake  { source, raw_message }
    ▼
Step 1: Ingestion  (Code node)
    │  Assigns ID, timestamp; normalises source; validates raw_message present
    ▼
Step 2: Classification  (HTTP → Groq API, response_format: json_object)
    │  LLM assigns: category, priority, confidence_score
    ▼
Parse Classification  (Code node)
    │  Parses JSON, validates category/priority/confidence against allowed values
    ▼
Step 3: Enrichment  (HTTP → Groq API, response_format: json_object)
    │  LLM extracts: core_issue, identifiers{}, urgency_signal
    ▼
Steps 4+6: Routing & Escalation  (Code node)
    │  Routing table → destination queue
    │  Escalation rules: confidence < 70% | keywords | billing > $200 | Incident category
    ▼
Step 5: Summary  (HTTP → Groq API)
    │  2–3 sentence handoff note for receiving team
    ▼
Assemble Final Record  (Code node)
    │  Flattens all fields into canonical output schema
    ├──► Output: Webhook.site  (POST full JSON record)
    ├──► Output: Google Sheets (append row — all 14 fields)
    └──► Webhook Response      (return JSON to caller)
```

### Output schema (per record)

```json
{
  "id":               "msg_1716000000000",
  "source":           "Email",
  "timestamp":        "2026-05-17T14:00:00.000Z",
  "raw_message":      "...",
  "category":         "Bug Report",
  "priority":         "High",
  "confidence_score": 0.94,
  "core_issue":       "User unable to log in due to 403 error after last week's update.",
  "identifiers": {
    "account_id":  "arcvault.io/user/jsmith",
    "error_code":  "403",
    "trigger_event": "platform update last Tuesday"
  },
  "urgency_signal":    "Access is fully blocked; issue started after a platform change.",
  "destination_queue": "Engineering",
  "routing_reason":    "Bug Report routes to Engineering",
  "escalation_flag":   false,
  "escalation_reason": null,
  "summary":           "User jsmith (arcvault.io/user/jsmith) is completely blocked from logging in with a 403 error that started after last Tuesday's update. The issue is high-priority and access-blocking. Engineering should check the auth middleware changes from the recent deployment and restore access."
}
```

### Escalation rules (in the Routing & Escalation node)

| Rule | Condition |
|---|---|
| Low confidence | `confidence_score < 0.70` |
| Outage keyword | message contains: `outage`, `down for all users`, `multiple users affected`, `stopped loading`, `completely down` |
| Billing discrepancy | extracted `identifiers.discrepancy > $200` |
| Incident category | category is `Incident / Outage` — always escalates |

---

## Running the Demo

### All 5 sample inputs — curl commands

```bash
# msg_001 — Bug Report → Engineering (no escalation)
curl -s -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Email","raw_message":"Hi, I tried logging in this morning and keep getting a 403 error. My account is arcvault.io/user/jsmith. This started after your update last Tuesday."}' | jq .

# msg_002 — Feature Request → Product (no escalation)
curl -s -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Web Form","raw_message":"We'\''d love to see a bulk export feature for our audit logs. We'\''re a compliance-heavy org and this would save us hours every month."}' | jq .

# msg_003 — Billing Issue → Escalation ($260 discrepancy > $200 threshold)
curl -s -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Support Portal","raw_message":"Invoice #8821 shows a charge of $1,240 but our contract rate is $980/month. Can someone look into this?"}' | jq .

# msg_004 — Technical Question → IT / Security (no escalation)
curl -s -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Email","raw_message":"I'\''m not sure if this is the right place to ask, but is there a way to set up SSO with Okta? We'\''re evaluating switching our auth provider."}' | jq .

# msg_005 — Incident / Outage → Escalation (keyword + category auto-escalate)
curl -s -X POST http://localhost:5678/webhook/arcvault-intake \
  -H "Content-Type: application/json" \
  -d '{"source":"Web Form","raw_message":"Your dashboard stopped loading for us around 2pm EST. Checked our end — it'\''s definitely on yours. Multiple users affected."}' | jq .
```

### Expected outputs

| Message | Category | Queue | Escalated | Reason |
|---|---|---|---|---|
| msg_001 (403 error) | Bug Report | Engineering | No | — |
| msg_002 (bulk export) | Feature Request | Product | No | — |
| msg_003 (invoice $260 over) | Billing Issue | Escalation | **Yes** | discrepancy $260 > $200 |
| msg_004 (Okta SSO) | Technical Question | IT / Security | No | — |
| msg_005 (outage, multiple users) | Incident / Outage | Escalation | **Yes** | keyword + category |

---

## Viewing Execution Results in n8n

After sending a curl request:

1. Left sidebar → **Executions**
2. Click the latest execution
3. Click any node to see its input and output data
4. **Assemble Final Record** → shows the complete flat JSON output schema
5. **Steps 4+6: Routing & Escalation** → shows the routing decision and escalation flag
6. **Output: Webhook.site** → shows the POST that was sent to Webhook.site
7. **Output: Google Sheets** → shows the row that was appended

---

## Suggested Demo Script (for Loom recording)

1. **Canvas walkthrough** (30 sec) — show all nodes left to right, name each step's role
2. **msg_003 — billing escalation** (60 sec) — send curl, open execution log, click Routing & Escalation node to show `escalation_flag: true` and reason; show Google Sheets row appended
3. **msg_005 — outage escalation** (60 sec) — show keyword match in routing node output
4. **msg_002 — clean non-escalated route** (30 sec) — show `destination_queue: "Product"`, no escalation
5. **Executions list** (20 sec) — all 5 runs completed with green checkmarks
6. **Webhook.site** (20 sec) — show the captured JSON records in your browser tab

Total: ~4 minutes

---

## Model Notes

**Groq `llama-3.3-70b-versatile`:**
- Free tier — no credit card, generous rate limits (14,400 requests/day, 500k tokens/min)
- `response_format: { type: "json_object" }` enforced at the API level for Steps 2 and 3 — the model is required to return valid JSON, not just asked to
- OpenAI-compatible API (`/v1/chat/completions`) — same format as GPT-4o; swap `model` string to switch providers
- To switch to Anthropic Sonnet: change the URL to `https://api.anthropic.com/v1/messages`, swap the auth header to `x-api-key`, and update the message format to Anthropic's schema (see `backend/app/pipeline/` for reference)

---

## Stop n8n

`Ctrl+C` in the terminal running `n8n start`.

Workflows and credentials persist in `~/.n8n` between restarts.
