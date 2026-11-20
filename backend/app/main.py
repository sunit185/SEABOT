from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.services.retrieval.bm25_index import init_fts
from app.workers.queue import JobQueue

# ---------------------------------------------------------------------------
# Logging setup (JSON structured)
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        log_obj = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def _setup_logging(log_file: str) -> None:
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = _JsonFormatter()

    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Job queue singleton
# ---------------------------------------------------------------------------

job_queue = JobQueue()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _setup_logging(settings.LOG_FILE)

    logger = logging.getLogger("seabot.startup")
    logger.info("Starting Seabot backend…")

    # Create data directories
    for subdir in ("uploads", "thumbnails", "logs", "chroma"):
        Path(settings.DATA_DIR, subdir).mkdir(parents=True, exist_ok=True)

    # Init DB tables
    await init_db()
    logger.info("Database initialised.")

    # Init FTS5 BM25 keyword index
    init_fts()
    logger.info("FTS5 BM25 index initialised.")

    # Start background job queue
    await job_queue.start()
    logger.info("Job queue started.")

    yield

    # Shutdown
    await job_queue.stop()
    logger.info("Seabot backend stopped.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

settings = get_settings()

app = FastAPI(
    title="Seabot API",
    description="Offline maritime RAG chatbot backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all localhost origins (frontend dev + packaged electron)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger = logging.getLogger("seabot.errors")
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": type(exc).__name__, "detail": str(exc)},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from app.routers import chat, documents, viewer, state, health  # noqa: E402

app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(viewer.router, prefix="/api")
app.include_router(state.router, prefix="/api")
app.include_router(health.router, prefix="/api")

# ---------------------------------------------------------------------------
# Static mounts
# ---------------------------------------------------------------------------

thumbnails_path = Path(settings.DATA_DIR) / "thumbnails"
thumbnails_path.mkdir(parents=True, exist_ok=True)
app.mount("/thumbnails", StaticFiles(directory=str(thumbnails_path)), name="thumbnails")

# Serve production frontend build if present
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
