"""Image validation unit tests."""

import io

import pytest
from PIL import Image

from app.core.exceptions import ImageValidationError
from app.utils.image_validation import validate_image_bytes


def _png(size=(32, 32)):
    buf = io.BytesIO()
    Image.new("RGB", size, (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_valid_png():
    img, fmt = validate_image_bytes(_png())
    assert fmt == "PNG"
    assert img.size == (32, 32)


def test_empty():
    with pytest.raises(ImageValidationError):
        validate_image_bytes(b"")


def test_not_image():
    with pytest.raises(ImageValidationError):
        validate_image_bytes(b"hello world")


def test_too_small():
    buf = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buf, format="PNG")
    with pytest.raises(ImageValidationError):
        validate_image_bytes(buf.getvalue())
