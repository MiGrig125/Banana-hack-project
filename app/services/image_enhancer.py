"""Local image enhancement (Pillow-based)."""

from pathlib import Path
from typing import Literal

from PIL import Image, ImageEnhance, ImageFilter

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.utils.file_storage import save_pil_image

logger = get_logger(__name__)
settings = get_settings()

EnhanceMode = Literal["auto", "sharpen", "contrast", "denoise", "upscale_basic"]


def enhance_image(image_path: Path, mode: str = "auto") -> Path:
    """
    Apply local enhancement.

    Modes:
      - sharpen: unsharp mask
      - contrast: auto contrast + slight brightness
      - denoise: mild median filter
      - upscale_basic: 2× nearest/bilinear resize (no generative AI)
      - auto: combination of denoise + contrast + sharpen

    Note: generative upscaling (Real-ESRGAN etc.) is not included by default
    to keep dependencies light and avoid large model downloads.
    """
    try:
        img = Image.open(image_path)
        img.load()
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.mode else "RGB")

        mode = (mode or "auto").lower()

        if mode == "upscale_basic":
            w, h = img.size
            img = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
        elif mode == "sharpen":
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        elif mode == "contrast":
            img = ImageEnhance.Contrast(img).enhance(1.25)
            img = ImageEnhance.Brightness(img).enhance(1.05)
        elif mode == "denoise":
            img = img.filter(ImageFilter.MedianFilter(size=3))
        else:  # auto
            img = img.filter(ImageFilter.MedianFilter(size=3))
            img = ImageEnhance.Contrast(img).enhance(1.15)
            img = ImageEnhance.Sharpness(img).enhance(1.3)
            img = ImageEnhance.Color(img).enhance(1.05)

        path = save_pil_image(img, settings.output_path, prefix="enhanced")
        return path
    except Exception as exc:
        logger.exception("Enhance failed")
        raise AppError(
            f"Ошибка улучшения изображения: {exc}",
            code="enhance_error",
            status_code=500,
        ) from exc
