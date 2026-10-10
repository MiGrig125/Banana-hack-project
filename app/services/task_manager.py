"""Simple in-process task tracking + DB history persistence."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.database import OperationHistory
from app.models.schemas import TaskStatus
from app.utils.file_storage import public_result_url

logger = get_logger(__name__)


def new_task_id() -> str:
    return uuid.uuid4().hex


def create_history(
    db: Session,
    *,
    task_id: str,
    operation_type: str,
    prompt: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    source_path: Optional[str] = None,
    status: str = TaskStatus.QUEUED.value,
) -> OperationHistory:
    row = OperationHistory(
        task_id=task_id,
        operation_type=operation_type,
        prompt=prompt,
        provider=provider,
        model=model,
        source_path=source_path,
        status=status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_history(
    db: Session,
    task_id: str,
    *,
    status: Optional[str] = None,
    result_path: Optional[str] = None,
    error_message: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[OperationHistory]:
    row = db.query(OperationHistory).filter(OperationHistory.task_id == task_id).first()
    if not row:
        return None
    if status is not None:
        row.status = status
        if status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value):
            row.completed_at = datetime.utcnow()
    if result_path is not None:
        row.result_path = result_path
    if error_message is not None:
        # Never store secrets
        row.error_message = error_message[:2000]
    if provider is not None:
        row.provider = provider
    if model is not None:
        row.model = model
    db.commit()
    db.refresh(row)
    return row


def get_history(db: Session, task_id: str) -> Optional[OperationHistory]:
    return db.query(OperationHistory).filter(OperationHistory.task_id == task_id).first()


def list_history(db: Session, limit: int = 50) -> List[OperationHistory]:
    return (
        db.query(OperationHistory)
        .order_by(OperationHistory.created_at.desc())
        .limit(limit)
        .all()
    )


def history_to_response(row: OperationHistory) -> Dict[str, Any]:
    result_url = None
    if row.result_path:
        try:
            result_url = public_result_url(Path(row.result_path))
        except Exception:
            result_url = None
    return {
        "task_id": row.task_id,
        "operation_type": row.operation_type,
        "prompt": row.prompt,
        "provider": row.provider,
        "model": row.model,
        "status": row.status,
        "result_url": result_url,
        "error_message": row.error_message,
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }
