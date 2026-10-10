"""Service layer for image editing."""

from pathlib import Path
from typing import List, Optional

from app.core.logging_config import get_logger
from app.providers.registry import registry
from app.utils.prompt_utils import clean_prompt

logger = get_logger(__name__)


async def edit(
    image_path: Path,
    prompt: str,
    *,
    mask_path: Optional[Path] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[List[Path], str, str]:
    """
    Edit an image according to the text prompt.

    Returns:
        (list of result paths, provider name, model name)
    """
    prompt = clean_prompt(prompt)
    if not prompt:
        raise ValueError("Промпт редактирования не может быть пустым.")

    if not image_path.is_file():
        raise FileNotFoundError("Исходное изображение не найдено.")

    prov = registry.get_editing(provider)
    if not prov.is_configured():
        from app.core.config import get_settings
        from app.core.exceptions import ProviderNotConfiguredError

        if get_settings().app_env == "development":
            logger.warning("Edit provider not configured — using mock")
            prov = registry.get_editing("mock")
        else:
            raise ProviderNotConfiguredError(prov.name)

    result = await prov.edit_image(
        image_path,
        prompt,
        mask_path=mask_path,
        model=model,
    )
    return result.images, result.provider, result.model
