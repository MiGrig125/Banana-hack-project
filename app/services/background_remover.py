"""Local background removal using rembg."""

from pathlib import Path
from typing import Optional

from PIL import Image

from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.core.config import get_settings
from app.utils.file_storage import save_pil_image

logger = get_logger(__name__)
settings = get_settings()

_session = None


def _get_session():
    """Lazy-load rembg session once."""
    global _session
    if _session is None:
        try:
            from rembg import new_session

            # u2net is widely available and does not require commercial licence
            _session = new_session("u2net")
            logger.info("rembg session (u2net) loaded")
        except Exception as exc:
            logger.exception("Failed to init rembg")
            raise AppError(
                "Не удалось загрузить модель удаления фона (rembg). "
                "Убедитесь, что пакет установлен: pip install \"rembg[cpu]\"",
                code="rembg_init_error",
                status_code=500,
            ) from exc
    return _session


def remove_background(image_path: Path) -> Path:
    """
    Remove background from an image and return path to PNG with alpha.

    Uses rembg with u2net model (runs locally, no API key).
    """
    try:
        from rembg import remove
    except ImportError as exc:
        raise AppError(
            "Библиотека rembg не установлена. Выполните: pip install \"rembg[cpu]\"",
            code="rembg_missing",
            status_code=500,
        ) from exc

    session = _get_session()
    try:
        input_img = Image.open(image_path)
        input_img.load()
        output = remove(input_img, session=session)
        if not isinstance(output, Image.Image):
            output = Image.open(output) if hasattr(output, "read") else Image.fromarray(output)
        path = save_pil_image(output, settings.output_path, prefix="nobg")
        return path
    except Exception as exc:
        logger.exception("Background removal failed")
        raise AppError(
            f"Ошибка при удалении фона: {exc}",
            code="bg_remove_error",
            status_code=500,
        ) from exc
