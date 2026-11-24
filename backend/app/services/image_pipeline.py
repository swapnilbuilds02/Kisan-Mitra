"""Image validation, compression, and hashing for the vision pipeline.

Guarantees:
- Only supported formats (JPEG/PNG/WebP) pass magic-byte validation.
- Images are resized/compressed before any external AI call.
- SHA-256 content hashes enable safe response caching for identical uploads.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_DIMENSION = 1024
JPEG_QUALITY = 85
MIN_DIMENSION = 64

SUPPORTED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

_MAGIC_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),
)


class ImageValidationError(Exception):
    """Input image rejected before any processing or AI call."""


class ImageTooLargeError(ImageValidationError):
    pass


class UnsupportedImageError(ImageValidationError):
    pass


class ImageProcessingError(ImageValidationError):
    pass


@dataclass(frozen=True)
class ProcessedImage:
    data: bytes
    mime_type: str
    content_hash: str
    width: int
    height: int
    original_bytes: int
    processed_bytes: int


def sniff_mime_type(raw: bytes) -> str | None:
    if len(raw) < 12:
        return None
    for signature, mime in _MAGIC_SIGNATURES:
        if raw.startswith(signature):
            if mime == "image/webp" and raw[8:12] != b"WEBP":
                return None
            return mime
    return None


def validate_image(raw: bytes) -> str:
    if not raw:
        raise UnsupportedImageError("Empty image upload.")
    if len(raw) > MAX_IMAGE_BYTES:
        raise ImageTooLargeError(
            f"Image exceeds the {MAX_IMAGE_BYTES // (1024 * 1024)} MB limit."
        )
    mime = sniff_mime_type(raw)
    if mime is None or mime not in SUPPORTED_MIME_TYPES:
        raise UnsupportedImageError("Unsupported image format. Use JPEG, PNG, or WebP.")
    return mime


def process_image(raw: bytes) -> ProcessedImage:
    original_mime = validate_image(raw)
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.load()
            width, height = img.size
            if width < MIN_DIMENSION or height < MIN_DIMENSION:
                raise ImageValidationError(
                    f"Image is too small ({width}x{height}); minimum is {MIN_DIMENSION}px."
                )
            resized = _resize_if_needed(img)
            if resized.mode not in ("RGB", "L"):
                resized = resized.convert("RGB")
            buffer = io.BytesIO()
            resized.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            processed = buffer.getvalue()
            out_width, out_height = resized.size
    except ImageValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageProcessingError("Image could not be decoded.") from exc

    return ProcessedImage(
        data=processed,
        mime_type="image/jpeg",
        content_hash=hashlib.sha256(processed).hexdigest(),
        width=out_width,
        height=out_height,
        original_bytes=len(raw),
        processed_bytes=len(processed),
    )


def _resize_if_needed(img: Image.Image) -> Image.Image:
    width, height = img.size
    longest = max(width, height)
    if longest <= MAX_IMAGE_DIMENSION:
        return img.copy()
    scale = MAX_IMAGE_DIMENSION / float(longest)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def content_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
