"""OpenAI Images API provider for generation and editing."""

import base64
from io import BytesIO
from pathlib import Path
from typing import Any, List, Optional

from openai import AsyncOpenAI, OpenAIError
from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import ProviderNotConfiguredError, ProviderUnavailableError
from app.core.logging_config import get_logger
from app.providers.base import GenerationResult, ImageEditingProvider, ImageGenerationProvider
from app.utils.file_storage import save_pil_image

logger = get_logger(__name__)
settings = get_settings()


class OpenAIImageProvider(ImageGenerationProvider, ImageEditingProvider):
    """
    Provider using OpenAI Images API (gpt-image-1 family).

    Docs: https://platform.openai.com/docs/guides/image-generation
    Endpoints: POST /v1/images/generations, POST /v1/images/edits
    """

    name = "openai"

    def __init__(self) -> None:
        self._client: Optional[AsyncOpenAI] = None
        if settings.openai_api_key:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    def is_configured(self) -> bool:
        return self._client is not None and bool(settings.openai_api_key)

    def supported_models(self) -> List[str]:
        return ["gpt-image-1", "gpt-image-1.5", "gpt-image-1-mini", "dall-e-3", "dall-e-2"]

    def supports_negative_prompt(self) -> bool:
        # GPT Image models do not expose a separate negative_prompt parameter
        return False

    def supports_seed(self) -> bool:
        return False

    def _require_client(self) -> AsyncOpenAI:
        if not self.is_configured() or self._client is None:
            raise ProviderNotConfiguredError("openai")
        return self._client

    def _size_string(self, width: Optional[int], height: Optional[int]) -> Optional[str]:
        if width and height:
            # Common sizes accepted by GPT Image / DALL·E
            return f"{width}x{height}"
        return None

    async def generate_image(
        self,
        prompt: str,
        *,
        negative_prompt: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        n: int = 1,
        seed: Optional[int] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> GenerationResult:
        client = self._require_client()
        model_name = model or settings.openai_image_model

        # Append negative guidance into prompt if provided (no dedicated param)
        full_prompt = prompt
        if negative_prompt:
            full_prompt = f"{prompt}\n\nAvoid: {negative_prompt}"

        params: dict[str, Any] = {
            "model": model_name,
            "prompt": full_prompt,
            "n": max(1, min(n, 4)),
        }
        size = self._size_string(width, height)
        if size:
            params["size"] = size

        try:
            response = await client.images.generate(**params)
        except OpenAIError as exc:
            logger.exception("OpenAI generate failed")
            raise ProviderUnavailableError(
                self._friendly_openai_error(exc), details=str(exc)
            ) from exc

        paths = self._save_response_images(response)
        return GenerationResult(
            images=paths,
            model=model_name,
            provider=self.name,
            meta={"count": len(paths)},
        )

    async def edit_image(
        self,
        image_path: Path,
        prompt: str,
        *,
        mask_path: Optional[Path] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> GenerationResult:
        client = self._require_client()
        model_name = model or settings.openai_image_model

        try:
            with open(image_path, "rb") as img_file:
                edit_kwargs: dict[str, Any] = {
                    "model": model_name,
                    "image": img_file,
                    "prompt": prompt,
                }
                if mask_path and mask_path.is_file():
                    with open(mask_path, "rb") as mask_file:
                        edit_kwargs["mask"] = mask_file
                        response = await client.images.edit(**edit_kwargs)
                else:
                    response = await client.images.edit(**edit_kwargs)
        except OpenAIError as exc:
            logger.exception("OpenAI edit failed")
            raise ProviderUnavailableError(
                self._friendly_openai_error(exc), details=str(exc)
            ) from exc

        paths = self._save_response_images(response)
        return GenerationResult(
            images=paths,
            model=model_name,
            provider=self.name,
            meta={"count": len(paths)},
        )

    def _save_response_images(self, response: Any) -> List[Path]:
        paths: List[Path] = []
        data = getattr(response, "data", None) or []
        for item in data:
            b64 = getattr(item, "b64_json", None)
            if not b64:
                # Some models may return URL; we prefer b64 for local storage
                url = getattr(item, "url", None)
                if url:
                    logger.warning("Received URL instead of b64_json; skipping download for safety")
                continue
            raw = base64.b64decode(b64)
            img = Image.open(BytesIO(raw))
            img.load()
            path = save_pil_image(img, settings.output_path, prefix="gen")
            paths.append(path)
        if not paths:
            raise ProviderUnavailableError("Провайдер не вернул изображение.")
        return paths

    @staticmethod
    def _friendly_openai_error(exc: Exception) -> str:
        msg = str(exc).lower()
        if "insufficient_quota" in msg or "billing" in msg:
            return "Недостаточно средств или исчерпан лимит OpenAI. Проверьте биллинг."
        if "rate_limit" in msg or "429" in msg:
            return "Превышен лимит запросов OpenAI. Попробуйте позже."
        if "invalid_api_key" in msg or "authentication" in msg:
            return "Неверный API-ключ OpenAI."
        if "content_policy" in msg or "safety" in msg:
            return "Запрос отклонён политикой безопасности модели."
        return "Ошибка при обращении к OpenAI Images API."
