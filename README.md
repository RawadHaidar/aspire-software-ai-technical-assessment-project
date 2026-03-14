# ArcVault Intake & Triage – Valsoft AI Engineer Assessment

This project implements an end‑to‑end AI‑powered intake and triage workflow for the fictional B2B SaaS product **ArcVault**, as described in the Valsoft AI Engineer take‑home assessment.

It uses:
- **FastAPI** as the workflow API.
- **OpenAI** for classification, enrichment, and summarization.
- A local **JSON file** (`outputs.json`) as the structured output store.

## 1. Features vs. Assessment Requirements

- **Step 1 – Ingestion**: `POST /process` endpoint accepts each inbound message (acts as a webhook/API trigger).
- **Step 2 – Classification**: LLM assigns `category`, `priority`, and `confidence`.
- **Step 3 – Enrichment**: Extracts `core_issue`, `entities`, and `urgency_signal`.
- **Step 4 – Routing**: Maps records to queues (Engineering, Billing, Product, Support, General) with a fallback.
- **Step 5 – Structured output**: Writes a full JSON record per message into `outputs.json` and returns it in the response.
- **Step 6 – Escalation**: Flags low‑confidence and high‑impact messages (`escalation_flag = true`) and routes them to an `Escalation` queue.

Additional documentation:
- `prompt_docs.md`: prompt design, reasoning, and trade‑offs.
- `architecture.md`: system design, routing/escalation logic, production considerations, and Phase 2 ideas.

## 2. Project Structure

- `main.py` – FastAPI app and HTTP endpoints.
- `models.py` – Pydantic models (`InboundMessage`, `EnrichedRecord`).
- `openai_client.py` – OpenAI client setup and LLM prompt/call.
- `processing.py` – Core pipeline, routing logic, and JSON persistence.
- `outputs.json` – Structured output records for all processed messages.
- `prompt_docs.md` – Prompt documentation (Section 4.3 deliverable).
- `architecture.md` – Architecture write‑up (Section 4.4 deliverable).
- `.env` – Local environment variables (ignored by Git).
- `.gitignore` – Excludes `.env`, `outputs.json`, and Python cache files.
- `requirements.txt` – Python dependencies.

## 3. Setup

### 3.1. Install dependencies

From the `project_folder` directory (ideally in a virtual environment):

```bash
pip install -r requirements.txt
```

### 3.2. Configure OpenAI

Create or edit `.env` in `project_folder`:

```env
OPENAI_API_KEY=sk-...your_real_key_here...
```

`.env` is listed in `.gitignore` so the key is not committed.

## 4. Running the Service

From `project_folder`:

```bash
uvicorn main:app --reload --port 8000
```

- Health check: open `http://127.0.0.1:8000/health` – expect `{"status": "ok"}`.
- Interactive API docs (Swagger UI): `http://127.0.0.1:8000/docs`.

## 5. Testing the Workflow

### 5.1. Using Swagger UI

1. Go to `http://127.0.0.1:8000/docs`.
2. Expand **`POST /process`**.
3. Click **“Try it out”**.
4. Paste a request body, for example:

```json
{
  "source": "Email",
  "raw_message": "Hi, I tried logging in this morning and keep getting a 403 error. My account is arcvault.io/user/jsmith. This started after your update last Tuesday."
}
```

5. Click **“Execute”**.

You will see an `EnrichedRecord` JSON response containing classification, enrichment, routing, and `escalation_flag`. The same record is appended to `outputs.json`.

Repeat with the remaining four sample messages from the assessment text to produce the full structured output file.

### 5.2. Structured Output File

- After processing all five sample inputs, `outputs.json` will contain one object per message.
- This file is the primary deliverable for **Section 4.2 – Structured Output File**.

## 6. Notes for Reviewers

- This repository is intentionally minimal and focused on clarity:
  - LLM responsibilities (classification/enrichment) are separated from deterministic routing and escalation.
  - All state is stored in a single JSON file for easy inspection.
- For production, see `architecture.md` for proposed improvements around reliability, cost, latency, and Phase 2 features.

