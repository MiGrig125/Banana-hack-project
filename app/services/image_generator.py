"""Service layer for image generation."""

from pathlib import Path
from typing import Any, List, Optional

from app.core.logging_config import get_logger
from app.providers.registry import registry
from app.utils.prompt_utils import clean_prompt

logger = get_logger(__name__)


async def generate(
    prompt: str,
    *,
    negative_prompt: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    n: int = 1,
    seed: Optional[int] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> tuple[List[Path], str, str]:
    """
    Generate image(s) via the selected provider.

    Returns:
        (list of result paths, provider name, model name)
    """
    prompt = clean_prompt(prompt)
    if not prompt:
        raise ValueError("Промпт не может быть пустым.")

    prov = registry.get_generation(provider)
    if not prov.is_configured():
        # Fall back to mock only in development for demo
        from app.core.config import get_settings

        

        raise ProviderNotConfiguredError(prov.name)

    result = await prov.generate_image(
        prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        n=n,
        seed=seed,
        model=model,
    )
    return result.images, result.provider, result.model
