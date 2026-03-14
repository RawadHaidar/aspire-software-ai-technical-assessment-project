from typing import List, Optional

from pydantic import BaseModel, Field


class InboundMessage(BaseModel):
    """Payload received from n8n / external caller."""

    source: str = Field(..., description="Origin of the message, e.g. Email, Web Form")
    raw_message: str = Field(..., description="Original unstructured message text")
    id: Optional[str] = Field(
        default=None,
        description="Optional external identifier. If missing, a timestamp-based ID is generated.",
    )


class EnrichedRecord(BaseModel):
    """Structured record after classification, enrichment, routing, and escalation."""

    id: str
    source: str
    raw_message: str

    # LLM-derived fields
    category: str
    priority: str
    confidence: float
    core_issue: str
    entities: List[str]
    urgency_signal: str
    summary: str

    # Routing and escalation
    destination_queue: str
    escalation_flag: bool

