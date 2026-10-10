"""Image analysis endpoints."""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError, ImageValidationError
from app.models.database import get_db
from app.models.schemas import TaskResponse, TaskStatus
from app.services import image_analyzer, task_manager
from app.utils.file_storage import save_upload
from app.utils.image_validation import validate_image_bytes

router = APIRouter()
settings = get_settings()


@router.post("/analyze", response_model=TaskResponse)
async def analyze_image(
    question: str = Form("Опиши подробно содержимое этого изображения."),
    image: UploadFile = File(...),
    model: str | None = Form(None),
    provider: str | None = Form(None),
    db: Session = Depends(get_db),
):
    task_id = task_manager.new_task_id()
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

    task_manager.create_history(
        db,
        task_id=task_id,
        operation_type="analyze",
        prompt=question,
        source_path=str(source),
        status=TaskStatus.PROCESSING.value,
    )
    try:
        text, prov, model_name = await image_analyzer.analyze(
            source, question, model=model, provider=provider
        )
        task_manager.update_history(
            db,
            task_id,
            status=TaskStatus.COMPLETED.value,
            provider=prov,
            model=model_name,
        )
        return TaskResponse(
            success=True,
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            analysis=text,
            message="Анализ выполнен",
            meta={"provider": prov, "model": model_name},
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
        )
    except Exception as exc:
        task_manager.update_history(
            db, task_id, status=TaskStatus.FAILED.value, error_message=str(exc)[:500]
        )
        return TaskResponse(
            success=False,
            task_id=task_id,
            status=TaskStatus.FAILED,
            error="Внутренняя ошибка при анализе",
            message="Внутренняя ошибка при анализе",
        )
