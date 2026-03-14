import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

try:
    # New OpenAI client (>=1.0.0)
    from openai import OpenAI

    _client: Optional[OpenAI] = None
except ImportError:  # pragma: no cover - fallback if openai not installed yet
    OpenAI = None  # type: ignore
    _client = None  # type: ignore

# Load environment variables from .env at import time
load_dotenv()


def get_openai_client() -> "OpenAI":
    """Lazily instantiate the OpenAI client."""
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Define it in a .env file or in your environment before running the FastAPI app."
        )

    _client = OpenAI(api_key=api_key)
    return _client


def call_openai(message: str) -> Dict[str, Any]:
    """
    Call OpenAI to classify and enrich a single inbound message.

    Returns a dict with:
    - category: one of ["Bug Report", "Feature Request", "Billing Issue", "Technical Question", "Incident/Outage"]
    - priority: one of ["Low", "Medium", "High"]
    - confidence: float 0–1
    - core_issue: one-sentence summary
    - entities: list of key identifiers
    - urgency_signal: one of ["Low", "Medium", "High"]
    - summary: 2–3 sentence human-readable summary
    """
    client = get_openai_client()

    system_prompt = """
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
"""

    try:
        # Use chat.completions for compatibility across OpenAI client versions
        response = client.chat.completions.create(
            model="gpt-5.4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
        )

        content = response.choices[0].message.content  # type: ignore[assignment]
        data = json.loads(content)
        return data
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Error calling OpenAI: {exc}") from exc

