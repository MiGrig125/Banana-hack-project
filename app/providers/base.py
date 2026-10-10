"""Abstract base classes for AI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class GenerationResult:
    """Result of an image generation or edit call."""

    images: List[Path]
    model: str
    provider: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """Result of an image analysis call."""

    text: str
    model: str
    provider: str
    meta: Dict[str, Any] = field(default_factory=dict)


class ImageGenerationProvider(ABC):
    """Interface for text-to-image providers."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def supported_models(self) -> List[str]:
        ...

    @abstractmethod
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
        ...

    def supports_negative_prompt(self) -> bool:
        return False

    def supports_seed(self) -> bool:
        return False


class ImageEditingProvider(ABC):
    """Interface for image editing providers."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def supported_models(self) -> List[str]:
        ...

    @abstractmethod
    async def edit_image(
        self,
        image_path: Path,
        prompt: str,
        *,
        mask_path: Optional[Path] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> GenerationResult:
        ...


class VisionProvider(ABC):
    """Interface for multimodal vision / analysis providers."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def supported_models(self) -> List[str]:
        ...

    @abstractmethod
    async def analyze_image(
        self,
        image_path: Path,
        question: str,
        *,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> AnalysisResult:
        ...
