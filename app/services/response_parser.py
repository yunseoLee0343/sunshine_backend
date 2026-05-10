"""ResponseParser — TICKET-018.

Parses the fixed-format LLM response ([결론][근거][행동][주의]) into
structured sections. Pure function, no I/O.
"""

from __future__ import annotations

from app.schemas.chat_answer import ParsedAnswer

_SECTIONS = ["결론", "근거", "행동", "주의"]


def parse_answer(content: str) -> ParsedAnswer:
    """Extract the four mandatory sections from LLM response text."""
    markers = [f"[{s}]" for s in _SECTIONS]

    positions: dict[str, int] = {}
    for section, marker in zip(_SECTIONS, markers):
        positions[section] = content.find(marker)

    extracted: dict[str, str] = {}
    for i, section in enumerate(_SECTIONS):
        start = positions[section]
        if start == -1:
            extracted[section] = ""
            continue
        start += len(f"[{section}]")
        end = len(content)
        for j in range(i + 1, len(_SECTIONS)):
            next_pos = positions[_SECTIONS[j]]
            if next_pos != -1 and next_pos > positions[section] and next_pos < end:
                end = next_pos
        extracted[section] = content[start:end].strip()

    return ParsedAnswer(
        결론=extracted.get("결론", ""),
        근거=extracted.get("근거", ""),
        행동=extracted.get("행동", ""),
        주의=extracted.get("주의", ""),
    )
