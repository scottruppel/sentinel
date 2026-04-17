"""Structured LLM output and API models."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Citation(BaseModel):
    title: str = ""
    source_url: str = ""
    published_at: str | None = None
    relevance: str = ""


class NarrativeAnalysis(BaseModel):
    """Auditable sections — not raw chain-of-thought."""

    facts_used: list[str] = Field(default_factory=list)
    interpretation: str = ""
    portfolio_impact: str = ""
    actions: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class MarketEventPublic(BaseModel):
    id: str
    title: str
    summary: str | None
    source_url: str
    published_at: str | None
    event_type: str | None
    region_tags: list[str]
    keywords: list[str]


class NarrativeRequest(BaseModel):
    use_llm: bool = True
    """If True and LLM configured, call model; else rules-only structured narrative."""

    allow_remote_llm: bool = False
    """Must be True to use non-localhost LLM base URL (when policy allows)."""


class NarrativeResponse(BaseModel):
    analysis: NarrativeAnalysis
    source: str  # "llm" | "rules"
    policy_version: str
    remote_llm_used: bool
    matched_events: list[MarketEventPublic] = Field(default_factory=list)
    raw_model_error: str | None = None


class IngestResult(BaseModel):
    inserted: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
