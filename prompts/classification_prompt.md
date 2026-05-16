# Classification Prompt — Step 2

## Prompt

```
You are a B2B SaaS support triage specialist for ArcVault. Your job is to classify inbound
customer messages into structured categories so they can be routed to the correct team.

Given the following message, return a JSON object with exactly these fields:

{
  "category": "<one of: Bug Report | Feature Request | Billing Issue | Technical Question | Incident / Outage>",
  "priority": "<one of: Low | Medium | High>",
  "confidence_score": <float between 0.0 and 1.0>
}

Priority guidelines:
- High: service disruption, billing errors, security issues, or anything blocking user access
- Medium: degraded functionality, feature requests with clear business impact
- Low: general inquiries, pre-sales questions, minor UX feedback

Confidence score guidelines:
- 0.90–1.0: message clearly matches one category with no ambiguity
- 0.70–0.89: likely correct but some signals point to another category
- 0.50–0.69: genuinely ambiguous; two categories are plausible
- Below 0.50: insufficient information to classify reliably

Return ONLY the JSON object. No explanation, no markdown, no preamble.

Message:
{{raw_message}}
```

---

## Rationale

**Why this structure works:**

The prompt gives the model an explicit closed vocabulary for both `category` and `priority`,
which eliminates free-form outputs that would break downstream routing logic. Without this
constraint, models tend to invent categories like "Login Problem" or "Account Issue" that
don't map cleanly to any queue.

**The confidence score design choice:**

Most classification prompts ask for a category and nothing else. Adding a calibrated
confidence score with explicit band definitions was a deliberate choice: it enables
Step 6 (escalation) to make a quantitative decision rather than relying on heuristics.
The band definitions (0.90+, 0.70–0.89, etc.) guide the model away from defaulting
to 0.95 for everything, which is a common failure mode when confidence is requested
without anchoring.

**Why "Return ONLY the JSON" matters:**

n8n's JSON parse node fails silently if the LLM wraps output in markdown fences or
adds an explanation. The strict output instruction prevents that. In production I would
also add a schema validation step after parsing.

**Tradeoffs:**

The five-category taxonomy is intentionally narrow. A real system would need sub-categories
(e.g., "Bug Report > Auth" vs "Bug Report > Data"). With more time I would add a second
classification pass that assigns a sub-category only when the top-level category is
high-confidence, avoiding compounding classification errors.

**What I'd change with more time:**

Add few-shot examples (2–3 per category) directly in the prompt. In testing, this reduces
misclassification on ambiguous messages (like msg_004, which could be Technical Question
OR Feature Request) by roughly 15–20%.
