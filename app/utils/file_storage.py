"""Safe local file storage helpers."""

import re
import uuid
from pathlib import Path
from typing import Optional

from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import StorageError
from app.utils.image_validation import extension_for_format

settings = get_settings()

SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def safe_filename(original: Optional[str] = None, suffix: str = ".png") -> str:
    """Generate a unique, path-traversal-safe filename."""
    base = uuid.uuid4().hex
    if original:
        cleaned = SAFE_NAME_RE.sub("_", Path(original).stem)[:40]
        if cleaned:
            base = f"{cleaned}_{base[:8]}"
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    return f"{base}{suffix}"


def save_upload(data: bytes, original_name: Optional[str] = None, fmt: str = "PNG") -> Path:
    """Save uploaded image bytes to the uploads directory."""
    ext = extension_for_format(fmt)
    name = safe_filename(original_name, ext)
    path = settings.upload_path / name
    try:
        path.write_bytes(data)
    except OSError as exc:
        raise StorageError(f"Не удалось сохранить загруженный файл: {exc}") from exc
    return path


def save_pil_image(img: Image.Image, directory: Path, prefix: str = "result") -> Path:
    """Save a PIL image to the given directory with a unique name."""
    directory.mkdir(parents=True, exist_ok=True)
    # Prefer PNG for transparency
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    ext = ".png" if has_alpha else ".jpg"
    name = safe_filename(prefix, ext)
    path = directory / name
    try:
        if ext == ".jpg":
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(path, format="JPEG", quality=92, optimize=True)
        else:
            img.save(path, format="PNG", optimize=True)
    except OSError as exc:
        raise StorageError(f"Не удалось сохранить результат: {exc}") from exc
    return path


def resolve_result_path(filename: str) -> Path:
    """
    Resolve a result filename safely (prevent path traversal).

    Only files inside the outputs directory are allowed.
    """
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise StorageError("Недопустимое имя файла.")

    path = (settings.output_path / filename).resolve()
    if not str(path).startswith(str(settings.output_path.resolve())):
        raise StorageError("Доступ запрещён.")

    if not path.is_file():
        raise StorageError("Файл не найден.")

    return path


def public_result_url(path: Path) -> str:
    """Return the public API URL for a stored result file."""
    return f"/api/results/{path.name}"
