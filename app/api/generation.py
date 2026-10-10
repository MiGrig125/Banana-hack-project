"""Image generation endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.database import get_db
from app.models.schemas import GenerateRequest, TaskResponse, TaskStatus
from app.services import image_generator, task_manager
from app.utils.file_storage import public_result_url

router = APIRouter()


@router.post("/generate", response_model=TaskResponse)
async def generate_image(body: GenerateRequest, db: Session = Depends(get_db)):
    task_id = task_manager.new_task_id()
    task_manager.create_history(
        db,
        task_id=task_id,
        operation_type="generate",
        prompt=body.prompt,
        status=TaskStatus.PROCESSING.value,
    )
    try:
        paths, provider, model = await image_generator.generate(
            body.prompt,
            negative_prompt=body.negative_prompt,
            width=body.width,
            height=body.height,
            n=body.n,
            seed=body.seed,
            model=body.model,
            provider=body.provider,
        )
        result_path = str(paths[0])
        task_manager.update_history(
            db,
            task_id,
            status=TaskStatus.COMPLETED.value,
            result_path=result_path,
            provider=provider,
            model=model,
        )
        urls = [public_result_url(p) for p in paths]
        return TaskResponse(
            success=True,
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result_url=urls[0],
            result_urls=urls,
            message="Изображение успешно сгенерировано",
            meta={"provider": provider, "model": model},
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
            error="Внутренняя ошибка при генерации",
            message="Внутренняя ошибка при генерации",
        )
