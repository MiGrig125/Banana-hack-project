"""Auto-process endpoint — AI Router driven."""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError, ImageValidationError
from app.models.database import get_db
from app.models.schemas import TaskResponse, TaskStatus
from app.services import (
    image_analyzer,
    image_editor,
    image_generator,
    task_manager,
)
from app.services.ai_router import Intent, route
from app.services.background_remover import remove_background
from app.services.image_enhancer import enhance_image
from app.utils.file_storage import public_result_url, save_upload
from app.utils.image_validation import validate_image_bytes

router = APIRouter()
settings = get_settings()


@router.post("/auto-process", response_model=TaskResponse)
async def auto_process(
    prompt: str = Form(...),
    image: Optional[UploadFile] = File(None),
    provider: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    task_id = task_manager.new_task_id()
    source: Optional[Path] = None

    if image is not None and image.filename:
        try:
            raw = await image.read()
            if len(raw) > settings.max_upload_bytes:
                raise ImageValidationError(
                    f"Размер файла превышает {settings.max_upload_size_mb} МБ."
                )
            _, fmt = validate_image_bytes(raw)
            source = save_upload(raw, image.filename, fmt)
        except ImageValidationError as exc:
            return TaskResponse(
                success=False,
                task_id=task_id,
                status=TaskStatus.FAILED,
                error=exc.message,
                message=exc.message,
            )

    route_result = route(prompt, has_image=source is not None)

    if route_result.clarification:
        return TaskResponse(
            success=False,
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=route_result.clarification,
            message=route_result.clarification,
            plan=[s.intent.value for s in route_result.plan],
        )

    if not route_result.plan:
        return TaskResponse(
            success=False,
            task_id=task_id,
            status=TaskStatus.FAILED,
            error="Не удалось определить операцию. Уточните запрос.",
            message="Не удалось определить операцию. Уточните запрос.",
        )

    plan_labels = [s.intent.value for s in route_result.plan]
    task_manager.create_history(
        db,
        task_id=task_id,
        operation_type="auto:" + "+".join(plan_labels),
        prompt=prompt,
        source_path=str(source) if source else None,
        status=TaskStatus.PROCESSING.value,
    )

    current_path = source
    last_result_url: Optional[str] = None
    analysis_text: Optional[str] = None
    used_provider = "local"
    used_model = "pipeline"

    try:
        for step in route_result.plan:
            intent = step.intent

            if intent == Intent.REMOVE_BACKGROUND:
                if current_path is None:
                    raise AppError("Нет изображения для удаления фона")
                current_path = remove_background(current_path)
                last_result_url = public_result_url(current_path)
                used_provider, used_model = "local", "rembg"

            elif intent == Intent.EDIT:
                if current_path is None:
                    raise AppError("Нет изображения для редактирования")
                paths, prov, model = await image_editor.edit(
                    current_path, prompt, provider=provider
                )
                current_path = paths[0]
                last_result_url = public_result_url(current_path)
                used_provider, used_model = prov, model

            elif intent == Intent.GENERATE:
                paths, prov, model = await image_generator.generate(
                    prompt, provider=provider
                )
                current_path = paths[0]
                last_result_url = public_result_url(current_path)
                used_provider, used_model = prov, model

            elif intent == Intent.ENHANCE:
                if current_path is None:
                    raise AppError("Нет изображения для улучшения")
                current_path = enhance_image(current_path, mode="auto")
                last_result_url = public_result_url(current_path)
                used_provider, used_model = "local", "pillow"

            elif intent == Intent.ANALYZE:
                if current_path is None:
                    raise AppError("Нет изображения для анализа")
                text, prov, model = await image_analyzer.analyze(
                    current_path, prompt, provider=provider
                )
                analysis_text = text
                used_provider, used_model = prov, model

        task_manager.update_history(
            db,
            task_id,
            status=TaskStatus.COMPLETED.value,
            result_path=str(current_path) if current_path else None,
            provider=used_provider,
            model=used_model,
        )
        return TaskResponse(
            success=True,
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result_url=last_result_url,
            analysis=analysis_text,
            plan=plan_labels,
            message="Обработка завершена",
            meta={"provider": used_provider, "model": used_model},
        )
    except AppError as exc:
        task_manager.update_history(
            db, task_id, status=TaskStatus.FAILED.value, error_message=exc.message
        )
        return TaskResponse(
            success=False,
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=exc.message,
            message=exc.message,
            plan=plan_labels,
        )
    except Exception as exc:
        task_manager.update_history(
            db, task_id, status=TaskStatus.FAILED.value, error_message=str(exc)[:500]
        )
        return TaskResponse(
            success=False,
            task_id=task_id,
            status=TaskStatus.FAILED,
            error="Ошибка авто-обработки",
            message="Ошибка авто-обработки",
            plan=plan_labels,
        )
