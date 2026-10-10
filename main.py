"""AI Photo Studio — application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging_config import setup_logging, get_logger
from app.models.database import init_db
from app.models.schemas import HealthResponse
from app.providers.registry import registry

settings = get_settings()
setup_logging("DEBUG" if settings.debug else "INFO")
logger = get_logger("main")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (%s)", settings.app_name, settings.app_env)
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.output_path.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.message,
            "code": exc.code,
        },
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": settings.app_name,
        },
    )

@app.get("/api/health", response_model=HealthResponse)
async def health():
    providers_status = {}
    for p in registry.list_providers():
        providers_status[p.name] = p.configured
    db_ok = True
    try:
        from app.models.database import SessionLocal
        from sqlalchemy import text

        with SessionLocal() as s:
            s.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        app=settings.app_name,
        providers=providers_status,
        database=db_ok,
    )


@app.get("/api/providers")
async def list_providers():
    return {"providers": [p.model_dump() for p in registry.list_providers()]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
