import json
import logging
import time
import traceback
from contextlib import asynccontextmanager

import mlflow
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from __version__ import __version__
from api.chat.router import router as chat_router
from api.parse.router import router as parse_router
from config import get_settings
from core.dto import ApiResponse
from core.exceptions import GraphExecutionError, LLMAPIError, LLMTimeoutError
from core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if settings.tracing.enabled:
        mlflow.set_tracking_uri(settings.tracing.uri)
        mlflow.set_experiment(settings.tracing.experiment)
        mlflow.langchain.autolog()
        logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)
        logger.info(
            "mlflow tracing enabled: uri=%s experiment=%s",
            settings.tracing.uri,
            settings.tracing.experiment,
        )
    else:
        logger.info("mlflow tracing disabled (TRACING__ENABLED=false)")
    logger.info("doc-editor-backend v%s started", __version__)

    yield
    logger.info("doc-editor-backend shutdown")


app = FastAPI(
    title="doc-editor-backend",
    version=__version__,
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parse_router, prefix="/api/parse", tags=["parse"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])


# ---------- Middleware ----------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    if request.url.path != "/health":
        logger.info(
            "Received %s",
            json.dumps({"method": request.method, "path": request.url.path}),
        )
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = time.perf_counter() - start_time
    if request.url.path != "/health":
        logger.info(
            "Finished %s",
            json.dumps(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "time": f"{process_time:.4f}",
                }
            ),
        )
    return response


# ---------- Root paths ----------
@app.get("/")
async def root() -> dict:
    return {"message": "doc-edit 2-poc2", "version": __version__}


@app.get("/health")
async def health_check() -> ORJSONResponse:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ok", "version": __version__},
    )


# ---------- Exception handlers ----------
def _error_response(code: int, label: str, exc: Exception) -> ORJSONResponse:
    traceback_msg = "".join(traceback.format_exception(exc))
    body = ApiResponse[str](code=code, message=f"[{label}] {exc!s}", data=traceback_msg)
    logger.error("[%s] %s", label, exc)
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=body.model_dump(),
    )


@app.exception_handler(LLMTimeoutError)
async def _llm_timeout_handler(request: Request, exc: LLMTimeoutError):
    return _error_response(2010, "LLMTimeoutError", exc)


@app.exception_handler(LLMAPIError)
async def _llm_api_handler(request: Request, exc: LLMAPIError):
    return _error_response(2000, "LLMAPIError", exc)


@app.exception_handler(GraphExecutionError)
async def _graph_handler(request: Request, exc: GraphExecutionError):
    return _error_response(3000, "GraphExecutionError", exc)


@app.exception_handler(Exception)
async def _unknown_handler(request: Request, exc: Exception):
    return _error_response(1000, "UnknownAPIError", exc)
