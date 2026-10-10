"""Service layer for image analysis."""

from pathlib import Path
from typing import Optional

from app.core.logging_config import get_logger
from app.providers.registry import registry
from app.utils.prompt_utils import clean_prompt

logger = get_logger(__name__)


async def analyze(
    image_path: Path,
    question: str,
    *,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[str, str, str]:
    """
    Analyze image content.

    Returns:
        (analysis text, provider name, model name)
    """
    question = clean_prompt(question) or "Опиши подробно содержимое этого изображения."

    if not image_path.is_file():
        raise FileNotFoundError("Изображение для анализа не найдено.")

    prov = registry.get_vision(provider)
    if not prov.is_configured():
        from app.core.config import get_settings
        from app.core.exceptions import ProviderNotConfiguredError

        if get_settings().app_env == "development":
            logger.warning("Vision provider not configured — using mock")
            prov = registry.get_vision("mock")
        else:
            raise ProviderNotConfiguredError(prov.name)

    result = await prov.analyze_image(image_path, question, model=model)
    return result.text, result.provider, result.model
