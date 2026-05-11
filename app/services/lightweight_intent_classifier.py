"""Lightweight (Stage 1) intent classifier — TICKET-013.

Pure regex / keyword matching. No DB, no LLM, no external I/O.
Returns a classified intent with confidence=0.95 on a strong match,
or None to signal that Stage 2 (mock LLM) should take over.
"""

from __future__ import annotations

import re

from app.schemas.chat_intent import Intent

# ---------------------------------------------------------------------------
# Compiled patterns — order matters only within each list; first match wins.
# ---------------------------------------------------------------------------

_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    intent: [re.compile(p, re.IGNORECASE) for p in patterns]
    for intent, patterns in {
        "watering_question": [
            r"물\s*[은을를]?\s*(줘|주기|주는|방법|언제|얼마|자주)",
            r"물.{1,20}(자주|언제|얼마)",  # 물 뒤 조사·어미 사이에 수식어
            r"(자주|언제|얼마나).{1,20}물",  # 역순: 자주/언제 → 물
            r"관수|물주기|water(?:ing)?",
            r"흙\s*이?\s*말라|건조\s*해|수분\s*부족|목말라|목이\s*말",
        ],
        "light_question": [
            r"빛\s*(이|을|는|가|양|세기|방향|조건)?|햇빛|햇살|일조",
            r"조도|광도|조명|직사\s*광선|그늘|그늘진",
            r"light|lux|루멘|lumens?|sunlight|shade",
        ],
        "humidity_question": [
            r"습도|습기|humidity",
            r"건조\s*(한|해지|해요)|공기\s*(가|이)\s*건조",
            r"가습|분무|촉촉",
        ],
        "temperature_question": [
            r"온도|기온|temperature",
            r"추위|추운|더위|더운|냉해|서리",
            r"겨울\s*(에|철|관리)|여름\s*(에|철|관리)",
            r"몇\s*도|영하|고온|저온",
        ],
        "species_care_question": [
            r"어떻게\s*(키|관리|돌봐)|키우는\s*방법|관리\s*(방법|요령)",
            r"(재배|생육)\s*(방법|조건|환경)",
            r"care\s*(guide|tips?)|how\s*to\s*(grow|care)",
            r"품종|변종|종류",
        ],
        "pest_reference_question": [
            r"해충|진딧물|응애|깍지벌레|총채벌레",
            r"잎\s*(이|이?\s*)(노랗|갈변|마름|썩|구멍|점)",
            r"병\s*(충해|든|이)\s*|감염|바이러스|곰팡이",
            r"pest|bug|insect|mite|fungus|rot",
        ],
        "companion_plant_question": [
            r"같이\s*(키|기르|심)|함께\s*(키|기르|심)",
            r"어울리|궁합|혼합\s*식재|혼식",
            r"companion\s*plant|mixed\s*planting",
            r"같은\s*화분|한\s*화분",
        ],
    }.items()
}

_CONFIDENCE_RULE = 0.95


class LightweightIntentClassifier:
    """Stage 1: regex-based classifier. Returns (intent, confidence) or None."""

    def classify(self, question: str) -> tuple[Intent, float] | None:
        for intent, patterns in _PATTERNS.items():
            for pat in patterns:
                if pat.search(question):
                    return intent, _CONFIDENCE_RULE  # type: ignore[return-value]
        return None
