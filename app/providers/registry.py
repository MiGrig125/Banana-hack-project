"""Provider registry — single place to discover available backends."""

from typing import Dict, List, Optional

from app.core.config import get_settings
from app.models.schemas import ProviderInfo
from app.providers.base import ImageEditingProvider, ImageGenerationProvider, VisionProvider
from app.providers.image_generation_provider import OpenAIImageProvider
from app.providers.vision_provider import OpenAIVisionProvider

settings = get_settings()


class MockImageProvider(ImageGenerationProvider, ImageEditingProvider):
    """Test-only provider that creates a solid-color placeholder image."""

    name = "mock"

    def is_configured(self) -> bool:
        return True

    def supported_models(self) -> List[str]:
        return ["mock-v1"]

    async def generate_image(self, prompt: str, **kwargs):
        from PIL import Image
        from app.utils.file_storage import save_pil_image

        img = Image.new("RGB", (512, 512), color=(40, 80, 120))
        path = save_pil_image(img, settings.output_path, prefix="mock")
        from app.providers.base import GenerationResult

        return GenerationResult(images=[path], model="mock-v1", provider=self.name)

    async def edit_image(self, image_path, prompt: str, **kwargs):
        return await self.generate_image(prompt)


class MockVisionProvider(VisionProvider):
    name = "mock"

    def is_configured(self) -> bool:
        return True

    def supported_models(self) -> List[str]:
        return ["mock-vision"]

    async def analyze_image(self, image_path, question: str, **kwargs):
        from app.providers.base import AnalysisResult

        return AnalysisResult(
            text=f"[MOCK] Анализ изображения. Вопрос: {question}",
            model="mock-vision",
            provider=self.name,
        )


class ProviderRegistry:
    """Holds registered generation, editing and vision providers."""

    def __init__(self) -> None:
        self._generation: Dict[str, ImageGenerationProvider] = {}
        self._editing: Dict[str, ImageEditingProvider] = {}
        self._vision: Dict[str, VisionProvider] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        openai_img = OpenAIImageProvider()
        self._generation["openai"] = openai_img
        self._editing["openai"] = openai_img
        self._vision["openai"] = OpenAIVisionProvider()

        # Mock always available for tests / demo without keys
        mock_img = MockImageProvider()
        self._generation["mock"] = mock_img
        self._editing["mock"] = mock_img
        self._vision["mock"] = MockVisionProvider()

    def get_generation(self, name: Optional[str] = None) -> ImageGenerationProvider:
        key = (name or settings.default_image_provider).lower()
        if key not in self._generation:
            key = "openai" if "openai" in self._generation else next(iter(self._generation))
        return self._generation[key]

    def get_editing(self, name: Optional[str] = None) -> ImageEditingProvider:
        key = (name or settings.default_image_provider).lower()
        if key not in self._editing:
            key = "openai" if "openai" in self._editing else next(iter(self._editing))
        return self._editing[key]

    def get_vision(self, name: Optional[str] = None) -> VisionProvider:
        key = (name or settings.default_vision_provider).lower()
        if key not in self._vision:
            key = "openai" if "openai" in self._vision else next(iter(self._vision))
        return self._vision[key]

    def list_providers(self) -> List[ProviderInfo]:
        names = set(self._generation) | set(self._editing) | set(self._vision)
        result: List[ProviderInfo] = []
        for name in sorted(names):
            caps: List[str] = []
            models: List[str] = []
            configured = False
            if name in self._generation:
                caps.append("generate")
                p = self._generation[name]
                configured = configured or p.is_configured()
                models.extend(p.supported_models())
            if name in self._editing:
                caps.append("edit")
                p = self._editing[name]
                configured = configured or p.is_configured()
            if name in self._vision:
                caps.append("analyze")
                p = self._vision[name]
                configured = configured or p.is_configured()
                models.extend(p.supported_models())
            # Local capabilities always available
            if name == "mock":
                configured = True
            result.append(
                ProviderInfo(
                    name=name,
                    configured=configured,
                    capabilities=sorted(set(caps)),
                    models=sorted(set(models)),
                )
            )
        # Add local tools as pseudo-providers for UI clarity
        result.append(
            ProviderInfo(
                name="local",
                configured=True,
                capabilities=["enhance", "remove_background"],
                models=["pillow", "rembg"],
            )
        )
        return result


# Singleton
registry = ProviderRegistry()
