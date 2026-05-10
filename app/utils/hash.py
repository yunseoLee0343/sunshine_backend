"""Stable hashing utilities — TICKET-017."""

from __future__ import annotations

import hashlib


def prompt_hash(text: str) -> str:
    """Return the SHA-256 hex digest of *text* encoded as UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def short_hash(text: str, length: int = 8) -> str:
    """Return the first *length* hex characters of SHA-256(*text*)."""
    return prompt_hash(text)[:length]
