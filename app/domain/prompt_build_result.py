"""PromptBuildResult domain object — TICKET-016.

Carries the generated system prompt, the user-turn string, metadata about
which guardrails were applied, and a SHA-256 hash of the prompt text for
traceability. Immutable once created.

No LLM calls, no DB access.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptBuildResult:
    """Output of PromptBuilder.build()."""

    system_prompt: str
    user_turn: str  # The user's question, verbatim
    intent: str
    guardrails_applied: tuple[str, ...]
    token_estimate: int  # Rough upper-bound; not used for billing
    prompt_hash: str  # SHA-256 hex of system_prompt


def build_prompt_result(
    *,
    system_prompt: str,
    user_turn: str,
    intent: str,
    guardrails_applied: list[str],
) -> PromptBuildResult:
    prompt_hash = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
    # Rough token estimate: Korean text averages ~1 token per character,
    # ASCII ~0.25.  We use a safe upper-bound of 1 token per character.
    token_estimate = len(system_prompt) + len(user_turn)
    return PromptBuildResult(
        system_prompt=system_prompt,
        user_turn=user_turn,
        intent=intent,
        guardrails_applied=tuple(sorted(guardrails_applied)),
        token_estimate=token_estimate,
        prompt_hash=prompt_hash,
    )
