"""PlantIdSpeciesClassifier — Plant.id API adapter for SpeciesClassifierPort.

Resolves the opaque image_ref to local bytes, encodes as base64, posts to
the Plant.id v3 identification endpoint, and normalises results into
SpeciesCandidate objects.

On any failure (network, timeout, bad key, unresolvable ref, malformed
response) the classifier returns the single "잘 모르겠어요" fallback so that
/plants/species-candidates never crashes because the external provider failed.
"""

import base64
import logging
from pathlib import Path

import httpx

from app.core.config import settings
from app.vision.species_classifier import SpeciesCandidate

logger = logging.getLogger(__name__)

_FALLBACK = SpeciesCandidate(
    label_ko="잘 모르겠어요",
    label_en="Unknown",
    scientific_name=None,
    confidence=0.0,
    confidence_label="low",
    source="plant.id",
)

_EXT_TO_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.80:
        return "high"
    if confidence >= 0.50:
        return "medium"
    return "low"


def _resolve_image_bytes(image_ref: str) -> bytes:
    """Load bytes from the local upload store.

    image_ref format: "uploads/plant-images/<uuid>.<ext>"
    UPLOAD_DIR default: "data/uploads"
    Full path: Path(UPLOAD_DIR).parent / image_ref  → "data/uploads/plant-images/<uuid>.<ext>"
    """
    path = Path(settings.UPLOAD_DIR).parent / image_ref
    return path.read_bytes()


def _parse_suggestions(
    suggestions: list[dict],
    locale: str,
    top_k: int,
) -> list[SpeciesCandidate]:
    lang = locale.split("-")[0].lower()  # "ko-KR" → "ko"
    candidates: list[SpeciesCandidate] = []

    for s in suggestions[: max(1, top_k)]:
        scientific_name: str | None = s.get("name") or None
        probability: float = float(s.get("probability") or 0.0)
        common_names: list[str] = (s.get("details") or {}).get("common_names") or []

        label_ko = common_names[0] if (lang == "ko" and common_names) else (scientific_name or "Unknown")
        label_en = scientific_name or "Unknown"

        candidates.append(
            SpeciesCandidate(
                label_ko=label_ko,
                label_en=label_en,
                scientific_name=scientific_name,
                confidence=probability,
                confidence_label=_confidence_label(probability),
                source="plant.id",
            )
        )

    return candidates


class PlantIdSpeciesClassifier:
    """Plant.id API adapter — implements SpeciesClassifierPort."""

    async def classify_species(
        self,
        image_ref: str,
        *,
        locale: str = "ko-KR",
        top_k: int = 3,
    ) -> list[SpeciesCandidate]:
        try:
            image_bytes = _resolve_image_bytes(image_ref)
        except Exception as exc:
            logger.warning("Cannot resolve image_ref %r: %s", image_ref, exc)
            return [_FALLBACK]

        mime = _EXT_TO_MIME.get(Path(image_ref).suffix.lower(), "image/jpeg")
        encoded = base64.b64encode(image_bytes).decode()
        lang = locale.split("-")[0].lower()

        payload = {
            "images": [f"data:{mime};base64,{encoded}"],
            "classification_level": "species",
            "language": lang,
        }
        headers = {
            "Api-Key": settings.PLANT_ID_API_KEY,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=settings.PLANT_ID_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{settings.PLANT_ID_API_URL.rstrip('/')}/identification",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.warning("Plant.id API request failed: %s", exc)
            return [_FALLBACK]

        try:
            suggestions: list[dict] = (
                data.get("result", {}).get("classification", {}).get("suggestions", [])
            )
            if not suggestions:
                return [_FALLBACK]
            candidates = _parse_suggestions(suggestions, locale, top_k)
            return candidates or [_FALLBACK]
        except Exception as exc:
            logger.warning("Failed to parse Plant.id response: %s", exc)
            return [_FALLBACK]
