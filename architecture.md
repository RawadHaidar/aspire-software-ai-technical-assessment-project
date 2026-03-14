# ArcVault Intake & Triage Workflow – Architecture Write-Up

## 1. System Design Overview

### Components

- **FastAPI service (`main.py`)**
  - Exposes a `POST /process` endpoint that accepts inbound customer messages.
  - Exposes a `GET /health` endpoint for simple liveness checks.

- **Domain models (`models.py`)**
  - `InboundMessage`: input schema with `source`, `raw_message`, and optional `id`.
  - `EnrichedRecord`: output schema capturing all classification, enrichment, routing, and escalation fields.

- **LLM integration (`openai_client.py`)**
  - Loads configuration from `.env` using `python-dotenv`.
  - Lazily instantiates the OpenAI client using `OPENAI_API_KEY`.
  - `call_openai(message: str)` encapsulates the prompt and API call, returning a structured Python `dict`.

- **Business logic & persistence (`processing.py`)**
  - `apply_routing(...)`: deterministic routing and escalation rules.
  - `append_to_file(...)`: appends each `EnrichedRecord` to `outputs.json`.
  - `process_message_internal(...)`: orchestrates the full pipeline for a single message.

- **Configuration & secrets**
  - `.env`: stores `OPENAI_API_KEY` (ignored by Git via `.gitignore`).
  - `requirements.txt`: declares FastAPI, Uvicorn, OpenAI, and python-dotenv.

### Data flow

1. A client (or workflow tool like n8n) sends a `POST` request to `/process` with an `InboundMessage` JSON payload.
2. FastAPI validates the payload against `InboundMessage` and passes it to `process_message_internal`.
3. `process_message_internal` calls `call_openai` with the raw message text.
4. The LLM returns a JSON object with classification and enrichment fields, which is parsed into a Python `dict`.
5. `apply_routing` enriches this dict with `destination_queue` and `escalation_flag` based on deterministic rules.
6. The final record is appended to `outputs.json` and returned to the client as an `EnrichedRecord` JSON response.
7. Over time, `outputs.json` accumulates one record per inbound message and can be submitted as the structured output artifact.

State is held only in:

- **`outputs.json`**: persistent, append-only record of processed messages.
- **Environment variables / `.env`**: configuration (OpenAI key).

Everything else is stateless across requests, which simplifies scaling and local testing.

## 2. Routing Logic

Routing is implemented in `apply_routing` in `processing.py`. It uses the LLM-derived `category` and `priority`, plus message content, to map each case to a destination queue:

- **Engineering**
  - `category` is `"Bug Report"` or `"Incident/Outage"`.

- **Billing**
  - `category` is `"Billing Issue"`.

- **Product**
  - `category` is `"Feature Request"`.

- **Support**
  - `category` is `"Technical Question"`.

- **General**
  - Any other or unexpected `category` values.

After initial mapping, the escalation logic may override `destination_queue` to `"Escalation"` when required (see next section). This split keeps the intent clear: first choose the “normal” queue, then apply an escalation layer that can redirect critical cases.

## 3. Escalation Logic

Escalation rules are also in `apply_routing`. They implement the assessment’s requirement to flag:

- Messages with **low model confidence**, and
- Messages that match defined escalation criteria (e.g., outage language, large billing errors).

Concretely:

1. **Low confidence**
   - If `confidence < 0.7`, `escalation_flag` is set to `True` and the `destination_queue` is forced to `"Escalation"`.

2. **Outage / incident keywords**
   - The `summary` text is lowercased and checked for phrases like:
     - `"outage"`, `"down for all users"`, `"dashboard stopped loading"`, `"cannot access"`, `"can't access"`.
   - If any match, escalation is triggered and the destination becomes `"Escalation"`.

3. **High-value billing issues**
   - If `category` is `"Billing Issue"` and the summary contains billing-related keywords/amounts (e.g., `"invoice"`, `"billing"`, `"charge"`, `"$1,240"`, `"$1240"`, `"$500"`), escalation is triggered.

These rules are intentionally transparent and easy to explain in an interview. They can be tuned or extended (e.g., configurable thresholds, more nuanced text patterns) without changing the LLM behavior.

## 4. Production-Scale Considerations

If this were moving toward production, I would consider the following changes:

- **Reliability & observability**
  - Add structured logging around each request, including timing, OpenAI errors, and escalation decisions.
  - Introduce metrics (e.g., via Prometheus) for counts of categories, escalations, and error rates.
  - Implement retry and graceful degradation when the LLM is unavailable (e.g., fall back to simpler rules or a cached model).

- **Cost control**
  - Cache repeated or highly similar messages (e.g., identical outage reports) to avoid redundant LLM calls.
  - Use a smaller/cheaper model for routine classifications and reserve larger models for ambiguous or escalated cases.
  - Batch processing for bulk historical data rather than one-call-per-record.

- **Latency**
  - Run the FastAPI service behind an async worker pool with connection pooling for the LLM client.
  - Optionally expose a queue-based ingestion API (e.g., Kafka, Redis) and process messages asynchronously, returning an immediate acknowledgment to upstream systems.

- **Persistence**
  - Replace `outputs.json` with a proper data store such as:
    - A relational database (PostgreSQL) for analytics and reporting.
    - A ticketing or case-management system via a webhook-based integration.

## 5. Phase 2 Ideas (If Given Another Week)

If I had additional time, I would explore:

- **UI and operations dashboard**
  - A simple front-end that shows the current queue, escalations, and key metrics.
  - Filters by category, priority, and escalation status.

- **Human-in-the-loop review**
  - A small interface for reviewers to:
    - Correct categories/priorities.
    - Mark escalations as valid or false positives.
    - Feed those corrections back into analytics or fine-tuning.

- **More advanced routing**
  - Incorporate customer-level metadata (e.g., plan tier, SLA, region) if available.
  - Use a rules engine or configuration file for routing rules so non-engineers can adjust queues and thresholds.

- **Model experimentation**
  - Compare multiple models (e.g., OpenAI vs Groq vs Mistral/Ollama) on a small labeled dataset to choose the best trade-off between accuracy, latency, and cost.
  - Add evaluation scripts that simulate the five sample messages plus additional synthetic cases and print confusion matrices.

Overall, the current implementation focuses on being simple, transparent, and aligned with the assessment requirements, while leaving clear upgrade paths for production-ready reliability and richer features.

