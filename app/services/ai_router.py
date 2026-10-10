"""AI Router — determines user intent and builds an execution plan."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from app.utils.prompt_utils import clean_prompt, contains_any


class Intent(str, Enum):
    GENERATE = "generate"
    EDIT = "edit"
    ANALYZE = "analyze"
    ENHANCE = "enhance"
    REMOVE_BACKGROUND = "remove_background"
    UNKNOWN = "unknown"


@dataclass
class PlanStep:
    intent: Intent
    prompt: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class RouteResult:
    intents: List[Intent]
    plan: List[PlanStep]
    needs_image: bool
    clarification: Optional[str] = None


# Keyword groups (Russian + English)
GENERATE_KW = [
    "сгенерируй", "создай", "нарисуй", "сгенерировать", "создать", "нарисовать",
    "generate", "create", "draw", "imagine", "картинку", "изображение по описанию",
    "фотореалистичн", "нарисуй мне",
]
EDIT_KW = [
    "отредактируй", "измени", "замени", "добавь", "убери объект", "удали объект",
    "поставь на", "перенеси", "сделай фон", "измени фон", "замени фон",
    "edit", "change", "replace", "add", "remove object", "put on", "style",
    "сделай реалистичн", "измени освещение", "замени небо",
]
ANALYZE_KW = [
    "опиши", "что на", "какие предметы", "распознай", "анализ", "проанализируй",
    "что изображено", "расскажи о", "extract text", "ocr", "describe", "what is",
    "какие объекты", "композиция", "освещение",
]
ENHANCE_KW = [
    "улучши", "увеличь разрешение", "повысь качество", "убери шум", "резкость",
    "enhance", "upscale", "sharpen", "denoise", "improve quality", "суперразрешение",
]
BG_KW = [
    "удали фон", "убери фон", "удалить фон", "remove background", "без фона",
    "прозрачный фон", "вырежи объект", "cut out",
]


def route(prompt: str, has_image: bool) -> RouteResult:
    """
    Classify user intent(s) from natural language.

    Supports multi-step plans, e.g.:
    «Удали фон, поставь автомобиль на ночную улицу Токио, улучши качество»
    → remove_background → edit → enhance
    """
    text = clean_prompt(prompt)
    if not text:
        return RouteResult(
            intents=[Intent.UNKNOWN],
            plan=[],
            needs_image=False,
            clarification="Введите текстовый запрос.",
        )

    lower = text.lower()
    found: List[Intent] = []

    if contains_any(lower, BG_KW):
        found.append(Intent.REMOVE_BACKGROUND)
    if contains_any(lower, ENHANCE_KW):
        found.append(Intent.ENHANCE)
    if contains_any(lower, ANALYZE_KW):
        found.append(Intent.ANALYZE)
    if contains_any(lower, EDIT_KW):
        found.append(Intent.EDIT)
    if contains_any(lower, GENERATE_KW):
        found.append(Intent.GENERATE)

    # Heuristics when no strong keywords
    if not found:
        if has_image:
            # Default for image + text without clear intent → edit
            found = [Intent.EDIT]
        else:
            found = [Intent.GENERATE]

    # Resolve conflicts
    # If both generate and edit and no image → generate
    if Intent.GENERATE in found and Intent.EDIT in found and not has_image:
        found = [i for i in found if i != Intent.EDIT]
    # If edit but no image → generate or ask
    if Intent.EDIT in found and not has_image and Intent.GENERATE not in found:
        return RouteResult(
            intents=[Intent.UNKNOWN],
            plan=[],
            needs_image=True,
            clarification="Для редактирования загрузите изображение.",
        )
    if Intent.ANALYZE in found and not has_image:
        return RouteResult(
            intents=[Intent.UNKNOWN],
            plan=[],
            needs_image=True,
            clarification="Для анализа загрузите изображение.",
        )
    if Intent.REMOVE_BACKGROUND in found and not has_image:
        return RouteResult(
            intents=[Intent.UNKNOWN],
            plan=[],
            needs_image=True,
            clarification="Для удаления фона загрузите изображение.",
        )
    if Intent.ENHANCE in found and not has_image and Intent.GENERATE not in found:
        return RouteResult(
            intents=[Intent.UNKNOWN],
            plan=[],
            needs_image=True,
            clarification="Для улучшения качества загрузите изображение.",
        )

    # Build ordered plan
    # Preferred order for composite: remove_bg → edit → enhance → analyze
    order = [
        Intent.REMOVE_BACKGROUND,
        Intent.EDIT,
        Intent.GENERATE,
        Intent.ENHANCE,
        Intent.ANALYZE,
    ]
    ordered = [i for i in order if i in found]

    plan: List[PlanStep] = []
    for intent in ordered:
        plan.append(PlanStep(intent=intent, prompt=text))

    needs_image = any(
        i in (Intent.EDIT, Intent.ANALYZE, Intent.ENHANCE, Intent.REMOVE_BACKGROUND)
        for i in ordered
    )

    return RouteResult(intents=ordered, plan=plan, needs_image=needs_image)
