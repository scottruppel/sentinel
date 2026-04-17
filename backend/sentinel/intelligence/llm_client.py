"""OpenAI-compatible chat completions (Ollama, LM Studio, vLLM, etc.)."""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from sentinel.config import settings
from sentinel.intelligence.schemas import NarrativeAnalysis

log = structlog.get_logger()

SYSTEM_PROMPT = """You are a supply chain risk analyst. Respond ONLY with valid JSON matching this schema:
{
  "facts_used": ["string", ...],
  "interpretation": "string",
  "portfolio_impact": "string",
  "actions": ["string", ...],
  "citations": [{"title": "", "source_url": "", "published_at": null, "relevance": ""}]
}
Ground market claims in the provided public_event snippets (citations). Do not invent distributor stock figures."""


def _is_localhost_url(url: str) -> bool:
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower()
        return host in ("localhost", "127.0.0.1", "::1")
    except Exception:
        return False


def may_call_remote_endpoint(allow_remote_llm: bool) -> bool:
    if allow_remote_llm:
        return True
    return _is_localhost_url(settings.llm_base_url)


def is_local_llm_endpoint() -> bool:
    """True when configured endpoint is localhost (Ollama/LM Studio on same machine)."""
    return _is_localhost_url(settings.llm_base_url)


async def complete_narrative_json(
    user_payload: dict[str, Any],
    allow_remote_llm: bool,
) -> tuple[NarrativeAnalysis | None, str | None]:
    """
    Returns (analysis, error_message).
    """
    if not settings.llm_enabled:
        return None, "LLM disabled in configuration"

    if not may_call_remote_endpoint(allow_remote_llm):
        return None, "Remote LLM blocked: set allow_remote_llm=true or use localhost LLM"

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(user_payload, default=str),
            },
        ],
        "temperature": 0.2,
        "max_tokens": settings.llm_max_tokens,
    }
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        log.warning("llm_request_failed", error=str(e))
        return None, str(e)

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    if not content:
        return None, "Empty LLM response"

    parsed = _extract_json_object(content)
    if not parsed:
        return None, "Could not parse JSON from model output"

    try:
        analysis = NarrativeAnalysis.model_validate(parsed)
        return analysis, None
    except Exception as e:
        return None, f"Validation error: {e}"


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None
