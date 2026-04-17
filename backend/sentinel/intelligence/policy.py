"""
Tier A/B/C data classification and redaction for LLM payloads.

Tier A — never sent to remote models by default (full BOM context, internal refs, program names).
Tier B — minimized structured intelligence (scores, factors, MPN, manufacturer, enrichment fields).
Tier C — public market events stored locally; safe to include titles/snippets in prompts.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


POLICY_VERSION = "2026.04.1"


class DataTier(str, Enum):
    A = "A"  # highly sensitive — local only unless explicit opt-in
    B = "B"  # structured risk/enrichment — minimized for LLM
    C = "C"  # public signals — URLs, headlines


@dataclass(frozen=True)
class RedactionPolicy:
    """Controls what may leave the trust boundary."""

    include_bom_name: bool = False
    include_program: bool = False
    include_source_filename: bool = False
    include_reference_designator: bool = False
    include_quantity: bool = False
    include_component_description: bool = False
    hash_component_ids: bool = True
    allow_remote_llm: bool = False

    def fingerprint(self) -> str:
        raw = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def stable_component_token(component_id: str) -> str:
    """Opaque token for logs/prompts (not reversible to UUID without salt)."""
    return hashlib.sha256(f"sentinel:comp:{component_id}".encode()).hexdigest()[:12]


def audit_payload_summary(tiers_included: list[str], remote: bool) -> dict[str, Any]:
    return {
        "policy_version": POLICY_VERSION,
        "tiers_included": tiers_included,
        "remote_llm": remote,
    }
