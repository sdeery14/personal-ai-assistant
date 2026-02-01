# Dockerfile for Personal AI Assistant - Chat API
# Uses uv for fast, reproducible dependency management

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files and README (needed by hatchling)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies using uv (no dev dependencies)
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY eval/ ./eval/
COPY migrations/ ./migrations/

# Set Python path to include src directory
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application using uv
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
