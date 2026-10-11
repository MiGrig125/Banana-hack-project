"""
xAI Grok Imagine — генерация и редактирование изображений.

API:
  POST https://api.x.ai/v1/images/generations
  POST https://api.x.ai/v1/images/edits

Ключ: XAI_API_KEY на https://console.x.ai
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any, List, Optional

import httpx
from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import ProviderNotConfiguredError, ProviderUnavailableError
from app.core.logging_config import get_logger
from app.providers.base import GenerationResult, ImageEditingProvider, ImageGenerationProvider
from app.utils.file_storage import save_pil_image

logger = get_logger(__name__)
settings = get_settings()

XAI_BASE = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-imagine-image-2.0"
TIMEOUT = 120.0


class XAIImagineProvider(ImageGenerationProvider, ImageEditingProvider):
    name = "xai"

    def __init__(self) -> None:
        self.api_key = settings.xai_api_key or None
        self.model = getattr(settings, "xai_image_model", None) or DEFAULT_MODEL
        if self.api_key:
            logger.info("xAI Imagine ready model=%s", self.model)
        else:
            logger.warning("XAI_API_KEY is empty")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def supported_models(self) -> List[str]:
        return [
            "grok-imagine-image-2.0",
            "grok-imagine-image",
            "grok-imagine-image-quality",
        ]

    def supports_negative_prompt(self) -> bool:
        return False

    def supports_seed(self) -> bool:
        return False

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _require_key(self) -> None:
        if not self.api_key:
            raise ProviderNotConfiguredError(
                "xai",
                message=(
                    "Grok Imagine не настроен. "
                    "Добавьте XAI_API_KEY в .env (https://console.x.ai)."
                ),
            )

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
        self._require_key()
        model_name = model or self.model
        full_prompt = prompt
        if negative_prompt:
            full_prompt = f"{prompt}\n\nAvoid: {negative_prompt}"

        body = {
            "model": model_name,
            "prompt": full_prompt,
            "n": max(1, min(n, 4)),
            "response_format": "url",
        }

        logger.info("xAI generate model=%s", model_name)
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    f"{XAI_BASE}/images/generations",
                    headers=self._headers(),
                    json=body,
                )
                if resp.status_code >= 400:
                    raise ProviderUnavailableError(self._friendly_error(resp))
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise ProviderUnavailableError(
                f"Таймаут xAI ({int(TIMEOUT)} с)."
            ) from exc
        except ProviderUnavailableError:
            raise
        except Exception as exc:
            logger.exception("xAI generate failed")
            raise ProviderUnavailableError(f"Ошибка xAI: {exc}") from exc

        paths = await self._save_from_response(data)
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
        self._require_key()
        model_name = model or self.model

        suffix = image_path.suffix.lower()
        mime = "image/png"
        if suffix in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        elif suffix == ".webp":
            mime = "image/webp"

        b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        data_uri = f"data:{mime};base64,{b64}"

        body = {
            "model": model_name,
            "prompt": prompt,
            "image": {"url": data_uri, "type": "image_url"},
            "response_format": "url",
        }

        logger.info("xAI edit model=%s", model_name)
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    f"{XAI_BASE}/images/edits",
                    headers=self._headers(),
                    json=body,
                )
                if resp.status_code >= 400:
                    raise ProviderUnavailableError(self._friendly_error(resp))
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise ProviderUnavailableError(
                f"Таймаут xAI edit ({int(TIMEOUT)} с)."
            ) from exc
        except ProviderUnavailableError:
            raise
        except Exception as exc:
            logger.exception("xAI edit failed")
            raise ProviderUnavailableError(f"Ошибка xAI edit: {exc}") from exc

        paths = await self._save_from_response(data)
        return GenerationResult(
            images=paths,
            model=model_name,
            provider=self.name,
            meta={"count": len(paths)},
        )

    async def _save_from_response(self, data: dict) -> List[Path]:
        items = data.get("data") or []
        paths: List[Path] = []
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            for item in items:
                b64 = item.get("b64_json")
                url = item.get("url")
                raw = None
                if b64:
                    raw = base64.b64decode(b64)
                elif url:
                    r = await client.get(url)
                    r.raise_for_status()
                    raw = r.content
                if not raw:
                    continue
                img = Image.open(BytesIO(raw))
                img.load()
                paths.append(save_pil_image(img, settings.output_path, prefix="grok"))
        if not paths:
            raise ProviderUnavailableError("xAI не вернул изображение.")
        return paths

    @staticmethod
    def _friendly_error(resp: httpx.Response) -> str:
        try:
            body = resp.json()
            msg = str(body.get("error", body))[:400]
        except Exception:
            msg = resp.text[:400]
        code = resp.status_code
        low = msg.lower()
        if code == 401 or "auth" in low or "api key" in low:
            return "Неверный XAI_API_KEY. Проверьте ключ на https://console.x.ai"
        if code == 429:
            return "Лимит запросов xAI. Подождите и попробуйте снова."
        if "quota" in low or "billing" in low or "credit" in low:
            return "Недостаточно средств xAI. Пополните баланс в console.x.ai"
        return f"xAI API HTTP {code}: {msg}"