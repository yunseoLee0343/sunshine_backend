"""MockVisionClient — deterministic keyword-based mock — TICKET-030.

Matches substrings of image_uri (case-insensitive) to produce stable,
non-diagnostic symptom observations.  No file I/O, no network calls.

All visual_symptoms use "~이/가 관찰됨" (observed) language to comply with
the T19 non-diagnostic guardrail.
"""

from __future__ import annotations

from app.services.vision_port import VisionAnalysisResult

_PEST_KEYWORDS = {"pest", "벌레", "mite", "응애", "aphid", "진딧물", "whitefly", "가루이"}
_YELLOW_KEYWORDS = {"yellow", "황변", "yellowing", "노란"}
_WILT_KEYWORDS = {"wilt", "시들", "wilting", "droop", "축"}
_SPOT_KEYWORDS = {"spot", "점", "spots", "반점", "black_spot"}
_HEALTHY_KEYWORDS = {"healthy", "건강", "fresh", "green"}


class MockVisionClient:
    """Stateless mock that maps URI keywords to VisionAnalysisResult.

    Priority order: pest > yellow > wilt > spot > healthy > generic.
    """

    async def analyze(
        self, image_uri: str, *, locale: str = "ko-KR"
    ) -> VisionAnalysisResult:
        key = image_uri.lower()

        if any(kw in key for kw in _PEST_KEYWORDS):
            return VisionAnalysisResult(
                visual_symptoms=[
                    "잎 표면에 미세 반점이 관찰됨",
                    "잎 뒷면에 거미줄 흔적이 관찰됨",
                ],
                detected_objects=["leaf", "webbing"],
                confidence=0.82,
                observation_note="해충 관련 증상이 관찰됨",
                source="mock_vision",
                suggests_pest=True,
            )

        if any(kw in key for kw in _YELLOW_KEYWORDS):
            return VisionAnalysisResult(
                visual_symptoms=[
                    "잎 색상이 황변된 것이 관찰됨",
                    "잎 가장자리 탈색이 관찰됨",
                ],
                detected_objects=["leaf", "yellowing"],
                confidence=0.75,
                observation_note="황변 증상이 관찰됨",
                source="mock_vision",
            )

        if any(kw in key for kw in _WILT_KEYWORDS):
            return VisionAnalysisResult(
                visual_symptoms=[
                    "잎이 처진 상태가 관찰됨",
                    "줄기 긴장도 감소가 관찰됨",
                ],
                detected_objects=["leaf", "stem"],
                confidence=0.70,
                observation_note="위조 증상이 관찰됨",
                source="mock_vision",
            )

        if any(kw in key for kw in _SPOT_KEYWORDS):
            return VisionAnalysisResult(
                visual_symptoms=[
                    "잎에 갈색 반점이 관찰됨",
                    "잎 끝 괴사가 관찰됨",
                ],
                detected_objects=["leaf", "spot"],
                confidence=0.68,
                observation_note="반점 및 괴사 증상이 관찰됨",
                source="mock_vision",
            )

        if any(kw in key for kw in _HEALTHY_KEYWORDS):
            return VisionAnalysisResult(
                visual_symptoms=[
                    "잎 색상이 균일하게 관찰됨",
                    "줄기 직립 상태가 관찰됨",
                ],
                detected_objects=["leaf", "stem"],
                confidence=0.90,
                observation_note="건강한 식물 상태가 관찰됨",
                source="mock_vision",
            )

        return VisionAnalysisResult(
            visual_symptoms=["식물 전체 형태가 관찰됨"],
            detected_objects=["plant"],
            confidence=0.50,
            observation_note="특별한 이상 증상이 관찰되지 않음",
            source="mock_vision",
        )
