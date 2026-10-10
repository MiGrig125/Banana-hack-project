"""Main API router aggregation and shared helpers."""

from fastapi import APIRouter

from app.api import analysis, editing, generation, history
from app.api import enhance as enhance_mod
from app.api import remove_bg as remove_bg_mod
from app.api import auto as auto_mod

api_router = APIRouter(prefix="/api")

api_router.include_router(generation.router, tags=["generation"])
api_router.include_router(editing.router, tags=["editing"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(enhance_mod.router, tags=["enhance"])
api_router.include_router(remove_bg_mod.router, tags=["remove-background"])
api_router.include_router(auto_mod.router, tags=["auto"])
api_router.include_router(history.router, tags=["history"])
