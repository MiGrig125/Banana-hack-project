"""History and results endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.exceptions import StorageError, TaskNotFoundError
from app.models.database import get_db
from app.models.schemas import HistoryItem, TaskResponse, TaskStatus
from app.services import task_manager
from app.utils.file_storage import resolve_result_path

router = APIRouter()


@router.get("/history", response_model=list[HistoryItem])
def get_history_list(limit: int = 50, db: Session = Depends(get_db)):
    rows = task_manager.list_history(db, limit=min(limit, 100))
    items = []
    for row in rows:
        data = task_manager.history_to_response(row)
        items.append(HistoryItem(**data))
    return items


@router.get("/history/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    row = task_manager.get_history(db, task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    data = task_manager.history_to_response(row)
    return TaskResponse(
        success=row.status == TaskStatus.COMPLETED.value,
        task_id=row.task_id,
        status=TaskStatus(row.status),
        result_url=data.get("result_url"),
        message=row.error_message if row.status == TaskStatus.FAILED.value else "OK",
        error=row.error_message if row.status == TaskStatus.FAILED.value else None,
        meta={"provider": row.provider, "model": row.model},
    )


@router.get("/results/{filename}")
def get_result_file(filename: str):
    try:
        path = resolve_result_path(filename)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc

    media = "image/png"
    if path.suffix.lower() in (".jpg", ".jpeg"):
        media = "image/jpeg"
    elif path.suffix.lower() == ".webp":
        media = "image/webp"

    return FileResponse(path, media_type=media, filename=path.name)
