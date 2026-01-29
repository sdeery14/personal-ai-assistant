"""Middleware for request processing and observability."""

from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to every request.

    - Generates UUID4 per request (or uses X-Correlation-Id header if present)
    - Stores in request.state.correlation_id
    - Binds to structlog context for all subsequent logging
    - Adds X-Correlation-Id response header
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request with correlation ID tracking."""
        # Use existing correlation ID from header or generate new one
        correlation_id = request.headers.get("X-Correlation-Id", str(uuid4()))

        # Store in request state for access by route handlers
        request.state.correlation_id = correlation_id

        # Bind to structlog context for automatic inclusion in all logs
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-Id"] = correlation_id

        return response
