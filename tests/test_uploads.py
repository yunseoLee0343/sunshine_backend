"""T-003B — Upload endpoint tests (no live DB or filesystem dependencies)."""

import asyncio
import io
from pathlib import Path
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from app.main import app

_JPEG = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b"\x00" * 100
_PNG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b"\x00" * 100
_WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 20


async def _upload(
    data: bytes,
    content_type: str = "image/jpeg",
    filename: str = "plant.jpg",
) -> tuple[int, dict]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/uploads/plant-image",
            files={"file": (filename, io.BytesIO(data), content_type)},
        )
    return r.status_code, r.json()


def _patched(tmp_path: Path):
    """Return a patch context that redirects uploads to tmp_path."""
    return patch(
        "app.api.uploads.settings",
        UPLOAD_DIR=str(tmp_path),
        UPLOAD_MAX_BYTES=10 * 1024 * 1024,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_upload_jpeg_returns_201(tmp_path: Path) -> None:
    with _patched(tmp_path):
        status, body = asyncio.run(_upload(_JPEG, "image/jpeg"))
    assert status == 201
    assert body["image_ref"].startswith("uploads/plant-images/")
    assert body["image_ref"].endswith(".jpg")
    assert body["content_type"] == "image/jpeg"
    assert body["size_bytes"] == len(_JPEG)


def test_upload_png_returns_201(tmp_path: Path) -> None:
    with _patched(tmp_path):
        status, body = asyncio.run(_upload(_PNG, "image/png", "plant.png"))
    assert status == 201
    assert body["image_ref"].endswith(".png")
    assert body["content_type"] == "image/png"


def test_upload_webp_returns_201(tmp_path: Path) -> None:
    with _patched(tmp_path):
        status, body = asyncio.run(_upload(_WEBP, "image/webp", "plant.webp"))
    assert status == 201
    assert body["image_ref"].endswith(".webp")
    assert body["content_type"] == "image/webp"


def test_upload_image_refs_are_unique(tmp_path: Path) -> None:
    with _patched(tmp_path):
        _, b1 = asyncio.run(_upload(_JPEG, "image/jpeg"))
        _, b2 = asyncio.run(_upload(_JPEG, "image/jpeg"))
    assert b1["image_ref"] != b2["image_ref"]


def test_upload_file_is_stored_on_disk(tmp_path: Path) -> None:
    with _patched(tmp_path):
        _, body = asyncio.run(_upload(_JPEG, "image/jpeg"))
    filename = Path(body["image_ref"]).name
    stored = tmp_path / "plant-images" / filename
    assert stored.exists()
    assert stored.read_bytes() == _JPEG


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_upload_pdf_returns_415(tmp_path: Path) -> None:
    with _patched(tmp_path):
        status, _ = asyncio.run(_upload(b"%PDF-1.4", "application/pdf", "doc.pdf"))
    assert status == 415


def test_upload_gif_returns_415(tmp_path: Path) -> None:
    with _patched(tmp_path):
        status, _ = asyncio.run(_upload(b"GIF89a", "image/gif", "anim.gif"))
    assert status == 415


def test_upload_too_large_returns_413(tmp_path: Path) -> None:
    with patch(
        "app.api.uploads.settings",
        UPLOAD_DIR=str(tmp_path),
        UPLOAD_MAX_BYTES=50,
    ):
        status, _ = asyncio.run(_upload(b"\xFF\xD8\xFF" + b"x" * 200, "image/jpeg"))
    assert status == 413
