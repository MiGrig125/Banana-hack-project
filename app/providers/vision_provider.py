"""OpenAI Vision provider for image analysis."""

import base64
from pathlib import Path
from typing import Any, List, Optional

from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings
from app.core.exceptions import ProviderNotConfiguredError, ProviderUnavailableError
from app.core.logging_config import get_logger
from app.providers.base import AnalysisResult, VisionProvider

logger = get_logger(__name__)
settings = get_settings()


class OpenAIVisionProvider(VisionProvider):
    """
    Multimodal analysis via Chat Completions (gpt-4o / gpt-4o-mini).

    Docs: https://platform.openai.com/docs/guides/vision
    """

    name = "openai"

    def __init__(self) -> None:
        self._client: Optional[AsyncOpenAI] = None
        if settings.openai_api_key:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    def is_configured(self) -> bool:
        return self._client is not None and bool(settings.openai_api_key)

    def supported_models(self) -> List[str]:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"]

    def _require_client(self) -> AsyncOpenAI:
        if not self.is_configured() or self._client is None:
            raise ProviderNotConfiguredError("openai")
        return self._client

    async def analyze_image(
        self,
        image_path: Path,
        question: str,
        *,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> AnalysisResult:
        client = self._require_client()
        model_name = model or settings.openai_vision_model

        mime = "image/png"
        suffix = image_path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        elif suffix == ".webp":
            mime = "image/webp"

        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        system = (
            "Ты — внимательный ассистент по анализу изображений. "
            "Описывай только то, что реально видно на фотографии. "
            "Не выдумывай детали, которых нет. "
            "Если чего-то не видно — честно скажи об этом."
        )

        try:
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    },
                ],
                max_tokens=1500,
            )
        except OpenAIError as exc:
            logger.exception("OpenAI vision failed")
            raise ProviderUnavailableError(
                "Ошибка при анализе изображения через OpenAI.", details=str(exc)
            ) from exc

        text = ""
        if response.choices:
            text = (response.choices[0].message.content or "").strip()

        if not text:
            raise ProviderUnavailableError("Модель не вернула текстовый ответ.")

        return AnalysisResult(
            text=text,
            model=model_name,
            provider=self.name,
        )
