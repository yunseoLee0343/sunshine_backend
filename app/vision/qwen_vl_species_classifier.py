"""QwenVLSpeciesClassifier — scaffold for future Qwen3-VL remote vLLM classifier.

Future implementation plan:
  image_ref -> resolve to local upload path
  -> read file bytes -> encode as base64 data URL
  -> POST /v1/chat/completions with multimodal message (image + prompt)
  -> parse JSON response into raw species guesses
  -> return list[SpeciesCandidate]
  -> SpeciesCandidateService then resolves each candidate against the
     Excel-only catalog (find_catalog_by_* methods)

No network call is made at import time or at construction time.
classify_species() raises NotImplementedError until the vLLM integration
is wired in a follow-up ticket.
"""

from app.vision.species_classifier import SpeciesCandidate


class QwenVLSpeciesClassifier:
    """Scaffold implementation of SpeciesClassifierPort backed by a Qwen3-VL vLLM endpoint.

    Raises ValueError at construction if base_url is empty so the missing
    configuration is caught at startup rather than at first request.
    """

    def __init__(
        self,
        base_url: str,
        model: str = "qwen3-vl",
        timeout_seconds: float = 120.0,
    ) -> None:
        if not base_url:
            raise ValueError(
                "QWEN_VL_BASE_URL must be set when SPECIES_CLASSIFIER_PROVIDER=qwen_vl"
            )
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def classify_species(
        self,
        image_ref: str,
        *,
        locale: str = "ko-KR",
        top_k: int = 3,
    ) -> list[SpeciesCandidate]:
        raise NotImplementedError(
            "QwenVLSpeciesClassifier.classify_species() is not yet implemented. "
            "See module docstring for the planned integration path."
        )
