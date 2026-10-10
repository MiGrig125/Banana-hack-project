"""AI Router unit tests."""

from app.services.ai_router import Intent, route


def test_generate_no_image():
    r = route("Создай фотореалистичный автомобиль на закате", has_image=False)
    assert Intent.GENERATE in r.intents
    assert not r.clarification


def test_edit_with_image():
    r = route("Замени фон на ночную улицу Токио", has_image=True)
    assert Intent.EDIT in r.intents


def test_edit_without_image():
    r = route("Замени фон на пляж", has_image=False)
    assert r.clarification is not None


def test_remove_bg():
    r = route("Удали фон у этой фотографии", has_image=True)
    assert Intent.REMOVE_BACKGROUND in r.intents


def test_analyze():
    r = route("Опиши что на фотографии", has_image=True)
    assert Intent.ANALYZE in r.intents


def test_composite():
    r = route(
        "Удали фон, поставь автомобиль на ночную улицу Токио, улучши качество",
        has_image=True,
    )
    assert Intent.REMOVE_BACKGROUND in r.intents
    assert Intent.EDIT in r.intents
    assert Intent.ENHANCE in r.intents
    assert len(r.plan) >= 2


def test_enhance():
    r = route("Увеличь разрешение и улучши резкость", has_image=True)
    assert Intent.ENHANCE in r.intents


def test_empty():
    r = route("   ", has_image=False)
    assert r.clarification is not None
