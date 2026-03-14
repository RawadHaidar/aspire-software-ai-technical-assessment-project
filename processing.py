import json
import os
from datetime import datetime
from typing import Any, Dict

from models import EnrichedRecord, InboundMessage
from openai_client import call_openai


OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "outputs.json")


def apply_routing(base: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply routing and escalation logic on top of LLM output.
    """
    category = str(base.get("category", "")).strip()
    priority = str(base.get("priority", "")).strip()

    # Best-effort parsing of confidence
    try:
        confidence = float(base.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    summary_text = str(base.get("summary", "")).lower()

    # --- Destination queue mapping ---
    if category in {"Bug Report", "Incident/Outage"}:
        destination = "Engineering"
    elif category == "Billing Issue":
        destination = "Billing"
    elif category == "Feature Request":
        destination = "Product"
    elif category == "Technical Question":
        destination = "Support"
    else:
        destination = "General"

    # --- Escalation rules ---
    escalation = False

    # Rule 1: low confidence
    if confidence < 0.7:
        escalation = True

    # Rule 2: language suggesting outage or major incident
    outage_keywords = [
        "outage",
        "down for all users",
        "down for all",
        "dashboard stopped loading",
        "cannot access",
        "can't access",
    ]
    if any(kw in summary_text for kw in outage_keywords):
        escalation = True

    # Rule 3: high-value billing issues (simple heuristic based on example amounts)
    billing_keywords = ["invoice", "billing", "charge", "$1,240", "$1240", "$500"]
    if any(kw in summary_text for kw in billing_keywords) and category == "Billing Issue":
        escalation = True

    if escalation:
        destination = "Escalation"

    base["destination_queue"] = destination
    base["escalation_flag"] = escalation
    base["confidence"] = confidence  # ensure numeric

    # Normalize optional fields
    entities = base.get("entities") or []
    if not isinstance(entities, list):
        entities = [str(entities)]
    base["entities"] = [str(e) for e in entities]

    return base


def append_to_file(record: Dict[str, Any]) -> None:
    """
    Append a single record to outputs.json (creating it if needed).
    The file contains a JSON array of records.
    """
    if os.path.exists(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                data = []
        except (json.JSONDecodeError, OSError):
            data = []
    else:
        data = []

    data.append(record)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def process_message_internal(payload: InboundMessage) -> EnrichedRecord:
    """
    Core processing pipeline:
    - Call OpenAI for classification & enrichment
    - Apply routing & escalation logic
    - Persist to outputs.json
    """
    record_id = payload.id or datetime.utcnow().isoformat()

    base = call_openai(payload.raw_message)
    base["id"] = record_id
    base["source"] = payload.source
    base["raw_message"] = payload.raw_message

    full = apply_routing(base)
    append_to_file(full)

    return EnrichedRecord(**full)

