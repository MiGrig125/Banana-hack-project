"""Image validation utilities — never trust client MIME or extension alone."""

from io import BytesIO
from typing import Set, Tuple

from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import ImageValidationError

settings = get_settings()

ALLOWED_FORMATS: Set[str] = {"JPEG", "PNG", "WEBP"}
ALLOWED_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp"}
FORMAT_TO_EXT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def validate_image_bytes(data: bytes) -> Tuple[Image.Image, str]:
    """
    Validate raw image bytes.

    Returns:
        (PIL Image in RGB or RGBA, detected format name)

    Raises:
        ImageValidationError on any validation failure.
    """
    if not data:
        raise ImageValidationError("Пустой файл.")

    if len(data) > settings.max_upload_bytes:
        raise ImageValidationError(
            f"Размер файла превышает лимит {settings.max_upload_size_mb} МБ."
        )

    try:
        img = Image.open(BytesIO(data))
        img.load()  # force full decode
    except Exception as exc:
        raise ImageValidationError(
            "Не удалось прочитать изображение. Поддерживаются JPEG, PNG, WEBP."
        ) from exc

    fmt = (img.format or "").upper()
    if fmt not in ALLOWED_FORMATS:
        raise ImageValidationError(
            f"Формат «{fmt or 'unknown'}» не поддерживается. Допустимы: JPEG, PNG, WEBP."
        )

    width, height = img.size
    if width < 16 or height < 16:
        raise ImageValidationError("Изображение слишком маленькое (минимум 16×16).")

    if width > settings.max_image_dimension or height > settings.max_image_dimension:
        raise ImageValidationError(
            f"Размер изображения превышает {settings.max_image_dimension} px."
        )

    # Normalize mode
    if img.mode not in ("RGB", "RGBA"):
        if img.mode in ("P", "LA"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

    return img, fmt


def extension_for_format(fmt: str) -> str:
    """Return safe file extension for a PIL format."""
    return FORMAT_TO_EXT.get(fmt.upper(), ".png")
