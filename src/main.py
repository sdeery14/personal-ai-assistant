"""FastAPI application initialization."""

from contextlib import asynccontextmanager
from uuid import uuid4

from dotenv import load_dotenv

# Load environment variables before anything else
load_dotenv()

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.admin import router as admin_router
from src.api.auth import router as auth_router
from src.api.conversations import router as conversations_router
from src.api.entities import router as entities_router
from src.api.memories import router as memories_router
from src.api.notifications import router as notifications_router
from src.api.schedules import router as schedules_router
from src.api.proactive import router as proactive_router
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

    # Initialize database connection pool and run migrations
    try:
        from src.database import init_database, run_migrations, close_database

        await init_database()
        await run_migrations()
        logger.info("database_initialized")
    except Exception as e:
        logger.warning(
            "database_initialization_failed",
            error=str(e),
            note="Continuing without database - memory features will be unavailable",
        )

    # Initialize Redis connection
    try:
        from src.services.redis_service import get_redis, close_redis

        await get_redis()
        logger.info("redis_initialized")
    except Exception as e:
        logger.warning(
            "redis_initialization_failed",
            error=str(e),
            note="Continuing without Redis - caching and rate limiting will be unavailable",
        )

    # Start deferred email processing task (if email is enabled)
    deferred_email_task = None
    if settings.notification_email_enabled:
        async def _process_deferred_loop():
            """Periodically process deferred emails."""
            while True:
                try:
                    await asyncio.sleep(60)
                    from src.services.email_service import EmailService
                    email_service = EmailService()
                    count = await email_service.process_deferred_emails()
                    if count > 0:
                        logger.info("deferred_email_cycle", processed=count)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning("deferred_email_cycle_error", error=str(e))

        import asyncio
        deferred_email_task = asyncio.create_task(_process_deferred_loop())
        logger.info("deferred_email_processor_started")

    # Start scheduler service (Feature 011)
    scheduler_service = None
    try:
        from src.services.scheduler_service import SchedulerService
        scheduler_service = SchedulerService()
        scheduler_service.start()
        logger.info("scheduler_service_started")
    except Exception as e:
        logger.warning(
            "scheduler_service_start_failed",
            error=str(e),
            note="Continuing without scheduler - scheduled tasks will not execute",
        )

    logger.info(
        "application_started",
        model=settings.openai_model,
        log_level=settings.log_level,
    )

    yield

    # Shutdown
    # Stop scheduler service
    if scheduler_service is not None:
        try:
            await scheduler_service.stop()
            logger.info("scheduler_service_stopped")
        except Exception:
            pass

    # Cancel deferred email processor
    if deferred_email_task is not None:
        deferred_email_task.cancel()
        try:
            await deferred_email_task
        except asyncio.CancelledError:
            pass
        logger.info("deferred_email_processor_stopped")

    # Drain pending memory writes before closing connections
    try:
        from src.services.memory_write_service import await_pending_writes

        await await_pending_writes(timeout=5.0)
        logger.info("pending_writes_drained")
    except Exception:
        pass

    try:
        from src.database import close_database

        await close_database()
    except Exception:
        pass

    try:
        from src.services.redis_service import close_redis

        await close_redis()
    except Exception:
        pass

    logger.info("application_shutdown")


app = FastAPI(
    title="Personal AI Assistant - Chat API",
    description="Streaming chat endpoint for interacting with LLM assistant",
    version="0.2.0",
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
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(conversations_router)
app.include_router(memories_router)
app.include_router(entities_router)
app.include_router(notifications_router)
app.include_router(schedules_router)
app.include_router(proactive_router)
app.include_router(router)
