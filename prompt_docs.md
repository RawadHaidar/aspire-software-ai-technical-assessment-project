# Prompt Documentation

This document describes the prompts used for the LLM step in the ArcVault intake and triage workflow, and the reasoning behind their structure.

## 1. Classification & Enrichment Prompt

**Location**: `openai_client.py` → `call_openai`  
**Used by**: `process_message_internal` in `processing.py`

### System Prompt (high-level behavior)

The system prompt sets the role and output contract:

```text
You are an assistant for a B2B SaaS support triage system called ArcVault.

Given a single inbound customer message, you MUST respond with a single valid JSON object with:
- category: one of ["Bug Report", "Feature Request", "Billing Issue", "Technical Question", "Incident/Outage"]
- priority: one of ["Low", "Medium", "High"]
- confidence: float between 0 and 1 (how certain you are about category and priority)
- core_issue: one-sentence summary of the core problem or request
- entities: list of key identifiers found in the text (account ids, invoice numbers, URLs, error codes, etc.). If none, use an empty list.
- urgency_signal: one of ["Low", "Medium", "High"], based on impact and language in the message
- summary: 2–3 sentence summary for the destination team, in plain language.

Rules:
- ONLY return the JSON object, no surrounding text.
- The JSON must be strictly valid and parseable.
```

The user message is simply the raw inbound request text.

### Why this structure?

- **Explicit schema**: Listing the exact keys and allowed values for `category`, `priority`, and `urgency_signal` greatly reduces variability and makes the model’s output easy to validate and route. It also aligns 1:1 with the assessment’s required fields.
- **Strict JSON contract**: Stating “ONLY return the JSON object” and “strictly valid and parseable” minimizes the chances of extra prose or malformed JSON, which simplifies parsing on the backend.
- **Separation of concerns**: The LLM focuses on semantic tasks (classification, summarization, entity extraction, urgency), while deterministic routing and escalation rules live in Python. This keeps routing logic transparent and testable.
- **Confidence score**: Having the model self-report a `confidence` score allows the escalation logic to behave differently when the model is unsure, as required by the spec.
- **Entities and urgency**: These fields provide a compact enrichment layer that a downstream team or system can use without re-parsing the original text.

### Trade-offs and what I’d change with more time

- **More structured validation**: Right now, validation relies on clear instructions and Pydantic models. With more time, I would add a post-processing step to normalize category/priority values (e.g., tolerate slight spelling variations) and reject/repair invalid JSON in a more robust way.
- **Few-shot examples**: The current prompt is instruction-only. To improve consistency, I would add a few high-quality examples for each category/priority combination, especially borderline cases like distinguishing “Bug Report” vs “Incident/Outage”.
- **Language and tone control**: For production, I would further constrain the `summary` style (e.g., no hedging language, explicit impact and user segment) so the output is more copy-paste-ready for ticketing tools.
- **Multi-step prompting**: If the model struggled with doing everything in one shot, I would consider a two-step approach (first classification/urgency, then enrichment/summary) to simplify each task and possibly reuse the classification step for analytics.

