"""Pydantic schemas for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OperationType(str, Enum):
    GENERATE = "generate"
    EDIT = "edit"
    ANALYZE = "analyze"
    ENHANCE = "enhance"
    REMOVE_BACKGROUND = "remove_background"
    AUTO = "auto"
    UNKNOWN = "unknown"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    negative_prompt: Optional[str] = Field(None, max_length=2000)
    width: Optional[int] = Field(None, ge=256, le=2048)
    height: Optional[int] = Field(None, ge=256, le=2048)
    n: int = Field(1, ge=1, le=4)
    seed: Optional[int] = None
    model: Optional[str] = None
    provider: Optional[str] = None


class EditRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    model: Optional[str] = None
    provider: Optional[str] = None


class AnalyzeRequest(BaseModel):
    question: str = Field(
        default="Опиши подробно содержимое этого изображения.",
        min_length=1,
        max_length=2000,
    )
    model: Optional[str] = None
    provider: Optional[str] = None


class EnhanceRequest(BaseModel):
    mode: str = Field(
        default="auto",
        description="auto | sharpen | contrast | denoise | upscale_basic",
    )


class AutoProcessRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    provider: Optional[str] = None


class ProviderInfo(BaseModel):
    name: str
    configured: bool
    capabilities: List[str]
    models: List[str] = []


class TaskResponse(BaseModel):
    success: bool
    task_id: str
    status: TaskStatus
    result_url: Optional[str] = None
    result_urls: Optional[List[str]] = None
    message: Optional[str] = None
    analysis: Optional[str] = None
    plan: Optional[List[str]] = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class HistoryItem(BaseModel):
    task_id: str
    operation_type: str
    prompt: Optional[str]
    provider: Optional[str]
    model: Optional[str]
    status: str
    result_url: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    app: str
    providers: Dict[str, bool]
    database: bool
