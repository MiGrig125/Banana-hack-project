"""Background removal endpoints."""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError, ImageValidationError
from app.models.database import get_db
from app.models.schemas import TaskResponse, TaskStatus
from app.services import task_manager
from app.services.background_remover import remove_background
from app.utils.file_storage import public_result_url, save_upload
from app.utils.image_validation import validate_image_bytes

router = APIRouter()
settings = get_settings()


@router.post("/remove-background", response_model=TaskResponse)
async def remove_bg(
    image: UploadFile = File(...),
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
        operation_type="remove_background",
        source_path=str(source),
        status=TaskStatus.PROCESSING.value,
        provider="local",
        model="rembg/u2net",
    )
    try:
        result = remove_background(source)
        task_manager.update_history(
            db,
            task_id,
            status=TaskStatus.COMPLETED.value,
            result_path=str(result),
            provider="local",
            model="rembg/u2net",
        )
        return TaskResponse(
            success=True,
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result_url=public_result_url(result),
            message="Фон успешно удалён (PNG с прозрачностью)",
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
            error="Ошибка удаления фона",
            message="Ошибка удаления фона",
        )
