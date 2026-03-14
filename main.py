from typing import Dict

from fastapi import FastAPI, HTTPException

from models import EnrichedRecord, InboundMessage
from processing import process_message_internal


app = FastAPI(title="ArcVault Intake & Triage API", version="1.0.0")


@app.post("/process", response_model=EnrichedRecord)
def process_endpoint(payload: InboundMessage) -> EnrichedRecord:
    """
    Process a single inbound message and return the enriched record.

    This is the endpoint that n8n should call (e.g., via HTTP Request node).
    """
    try:
        return process_message_internal(payload)
    except RuntimeError as exc:
        # Typically raised for OpenAI or configuration issues
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # pragma: no cover - generic safeguard
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}

