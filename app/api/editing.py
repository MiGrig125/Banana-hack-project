"""Image editing endpoints."""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError, ImageValidationError
from app.models.database import get_db
from app.models.schemas import TaskResponse, TaskStatus
from app.services import image_editor, task_manager
from app.utils.file_storage import public_result_url, save_upload
from app.utils.image_validation import validate_image_bytes

router = APIRouter()
settings = get_settings()


@router.post("/edit", response_model=TaskResponse)
async def edit_image(
    prompt: str = Form(...),
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
        pil_img, fmt = validate_image_bytes(raw)
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
        operation_type="edit",
        prompt=prompt,
        source_path=str(source),
        status=TaskStatus.PROCESSING.value,
    )
    try:
        paths, prov, model_name = await image_editor.edit(
            source, prompt, model=model, provider=provider
        )
        result_path = str(paths[0])
        task_manager.update_history(
            db,
            task_id,
            status=TaskStatus.COMPLETED.value,
            result_path=result_path,
            provider=prov,
            model=model_name,
        )
        urls = [public_result_url(p) for p in paths]
        return TaskResponse(
            success=True,
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result_url=urls[0],
            result_urls=urls,
            message="Изображение успешно отредактировано",
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
            error="Внутренняя ошибка при редактировании",
            message="Внутренняя ошибка при редактировании",
        )
