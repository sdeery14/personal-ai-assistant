"""FastAPI application initialization."""

from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.middleware import CorrelationIdMiddleware
from src.api.routes import router
from src.config import get_settings
from src.services.logging_service import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("main")
    logger.info(
        "application_started",
        model=settings.openai_model,
        log_level=settings.log_level,
    )

    yield

    # Shutdown
    logger.info("application_shutdown")


app = FastAPI(
    title="Personal AI Assistant - Chat API",
    description="Streaming chat endpoint for interacting with LLM assistant",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with user-friendly messages.

    Returns 400 Bad Request with constitutional UX pattern:
    - What happened (error type)
    - Why (validation details)
    - What to do (implied in details)
    """
    # Use correlation ID from middleware if available, otherwise generate
    correlation_id = getattr(request.state, "correlation_id", None) or str(uuid4())
    logger = structlog.get_logger()

    # Extract validation error details
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        field = ".".join(str(loc) for loc in first_error.get("loc", ["unknown"]))
        message = first_error.get("msg", "Validation failed")
        detail = f"Field '{field}': {message}"
    else:
        detail = "Request validation failed"

    logger.warning(
        "validation_error",
        correlation_id=correlation_id,
        detail=detail,
        errors=errors,
    )

    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation error",
            "detail": detail,
            "correlation_id": correlation_id,
        },
        headers={"X-Correlation-Id": correlation_id},
    )


# CORS middleware for browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation ID middleware for request tracking and observability
app.add_middleware(CorrelationIdMiddleware)

# Include API routes
app.include_router(router)
