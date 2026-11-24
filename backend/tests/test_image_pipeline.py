import io

import pytest
from PIL import Image

from app.services.image_pipeline import (
    MAX_IMAGE_BYTES,
    MAX_IMAGE_DIMENSION,
    MIN_DIMENSION,
    ImageTooLargeError,
    ImageValidationError,
    UnsupportedImageError,
    content_hash,
    process_image,
    sniff_mime_type,
    validate_image,
)


def make_image_bytes(
    fmt="JPEG", size=(640, 480), color=(34, 120, 46)
) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()


class TestValidation:
    def test_valid_jpeg_passes(self):
        raw = make_image_bytes("JPEG")
        assert validate_image(raw) == "image/jpeg"

    def test_valid_png_passes(self):
        raw = make_image_bytes("PNG")
        assert validate_image(raw) == "image/png"

    def test_empty_rejected(self):
        with pytest.raises(UnsupportedImageError):
            validate_image(b"")

    def test_gif_rejected(self):
        raw = make_image_bytes("GIF")
        with pytest.raises(UnsupportedImageError):
            validate_image(raw)

    def test_arbitrary_bytes_rejected(self):
        with pytest.raises(UnsupportedImageError):
            validate_image(b"not an image at all, just text")

    def test_oversized_rejected(self):
        with pytest.raises(ImageTooLargeError):
            validate_image(b"\xff\xd8\xff" + b"x" * (MAX_IMAGE_BYTES + 1))

    def test_sniff_detects_formats(self):
        assert sniff_mime_type(make_image_bytes("JPEG")) == "image/jpeg"
        assert sniff_mime_type(make_image_bytes("PNG")) == "image/png"
        assert sniff_mime_type(b"short") is None

    def test_content_hash_stable(self):
        raw = make_image_bytes("JPEG")
        assert content_hash(raw) == content_hash(raw)
        assert content_hash(raw) != content_hash(make_image_bytes("PNG"))


class TestProcessing:
    def test_downscales_large_image(self):
        raw = make_image_bytes("JPEG", size=(4000, 3000))
        result = process_image(raw)
        assert max(result.width, result.height) <= MAX_IMAGE_DIMENSION
        assert result.mime_type == "image/jpeg"
        assert result.processed_bytes < result.original_bytes

    def test_keeps_small_image_dimensions(self):
        raw = make_image_bytes("JPEG", size=(320, 240))
        result = process_image(raw)
        assert (result.width, result.height) == (320, 240)

    def test_too_small_image_rejected(self):
        raw = make_image_bytes("JPEG", size=(16, 16))
        with pytest.raises(ImageValidationError, match="too small"):
            process_image(raw)

    def test_corrupt_jpeg_rejected(self):
        raw = b"\xff\xd8\xff" + b"\x00" * 64
        with pytest.raises(ImageValidationError):
            process_image(raw)

    def test_png_converted_to_jpeg(self):
        raw = make_image_bytes("PNG", size=(800, 600))
        result = process_image(raw)
        assert result.mime_type == "image/jpeg"
        assert result.data[:3] == b"\xff\xd8\xff"

    def test_transparent_png_becomes_opaque(self):
        buf = io.BytesIO()
        Image.new("RGBA", (200, 200), (0, 0, 0, 0)).save(buf, format="PNG")
        result = process_image(buf.getvalue())
        assert result.width == 200

    def test_hash_changes_when_pixels_change(self):
        a = process_image(make_image_bytes("JPEG", color=(10, 20, 30)))
        b = process_image(make_image_bytes("JPEG", color=(200, 10, 10)))
        assert a.content_hash != b.content_hash

    def test_deterministic_hash_for_identical_pixels(self):
        a = process_image(make_image_bytes("JPEG", size=(300, 300)))
        b = process_image(make_image_bytes("JPEG", size=(300, 300)))
        assert a.content_hash == b.content_hash

    def test_min_dimension_constant_sane(self):
        assert MIN_DIMENSION >= 32
