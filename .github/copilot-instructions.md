# Copilot Instructions (Repository)

## Docker-First Development (CRITICAL)

**All services run in Docker containers. This is the production setup and our development standard.**

### Service Architecture

- **Chat API**: Runs in Docker via `docker compose -f docker/docker-compose.api.yml up -d`
- **MLflow**: Runs in Docker via `docker compose -f docker/docker-compose.mlflow.yml up -d`
- **Tests**: Run from host machine using `uv run pytest`, but test AGAINST Dockerized services
- **Eval**: Run from host machine using `uv run python -m eval`, requires MLflow in Docker

### Development Workflow

1. **Start services**: `docker compose -f docker/docker-compose.mlflow.yml up -d && docker compose -f docker/docker-compose.api.yml up -d --env-file .env`
2. **Make code changes**: Edit files locally
3. **Rebuild & restart**: `docker compose -f docker/docker-compose.api.yml up -d --build`
4. **Run tests**: `uv run pytest tests/` (tests hit Docker containers on localhost:8000)
5. **Run evals**: `uv run python -m eval` (logs to MLflow in Docker on localhost:5000)
6. **View logs**: `docker logs chat-api -f` or `docker logs mlflow-server -f`
7. **Stop services**: `docker compose -f docker/docker-compose.api.yml down && docker compose -f docker/docker-compose.mlflow.yml down`

### Why Docker-First?

- **Production parity**: Test the actual deployment setup
- **Service dependencies**: As services grow interconnected, Docker orchestration becomes essential
- **Environment consistency**: Same behavior across dev/staging/prod
- **Integration testing**: Real service-to-service communication (API → MLflow, etc.)

### When to Use Local Python

- **Unit tests only**: `uv run pytest tests/unit/` - these mock everything, no services needed
- **Linting/formatting**: `uv run ruff check src/`
- **Dependency management**: `uv add <package>` then rebuild containers

## Python dependency management (IMPORTANT)

- This repo uses `uv` for dependency management.
- Do NOT suggest `pip install ...` or `python -m pip ...` as the default.
- Assume dependencies are declared in `pyproject.toml` and a lockfile is used.

### Preferred commands

- Install/sync dependencies: `uv sync`
- Add a dependency: `uv add <package>`
- Add a dev dependency: `uv add --dev <package>`
- Run commands in the project env: `uv run <command>`
- Run tests: `uv run pytest` (or the repo’s test runner)

### Behavior

- When giving setup instructions, provide the `uv` “golden path” first.
- If you mention `pip`, label it explicitly as an exception and explain why.

## Testing Philosophy (IMPORTANT)

### pytest - Code Testing Only

- **Purpose**: Test code logic, error handling, data structures, and control flow
- **No real AI API calls**: Mock all OpenAI/LLM API calls (moderation, completions, embeddings, etc.)
- **Fast, deterministic, cheap**: Tests should run in seconds and always produce same results
- **What to test**:
  - Unit tests: Individual functions, classes, data transformations
  - Integration tests: API endpoints, database interactions, service orchestration
  - Error scenarios: Retries, timeouts, exception handling, edge cases
- **What NOT to test**: AI output quality, prompt effectiveness, model behavior

### MLflow Eval - AI Quality Testing

- **Purpose**: Test AI behavior, output quality, safety, and prompt effectiveness
- **Real AI API calls required**: Actual model inference and judge evaluation
- **Slow, non-deterministic, expensive**: Tests take minutes and results may vary
- **What to test**:
  - Golden datasets: Expected outputs for known inputs
  - Security red-teaming: Adversarial prompts and guardrail effectiveness
  - Quality metrics: Judge-based scoring, block rates, false positive rates
  - Regression gating: Ensure quality metrics don't degrade over time
- **Implementation**: Use `eval/` module with MLflow tracking

### Guidelines

- When implementing a new AI feature: Write pytest for code paths, write MLflow eval for AI quality
- When debugging: Start with pytest for logic bugs, use MLflow eval for quality issues
- CI/CD: Run pytest on every commit, run MLflow eval on nightly/release builds
- Never mock the entire SDK/Runner in pytest - if you need to test SDK integration, that's an MLflow eval test

### Testing Against Docker Services

- **Unit tests**: Mock everything, no Docker needed (fast, isolated)
- **Integration tests**: Hit Docker services at localhost:8000 (requires `docker compose up`)
- **Eval tests**: Require MLflow running in Docker at localhost:5000
- **Test execution**: Always run from host with `uv run pytest` (NOT inside container)

## General

- Prefer cross-platform commands (Windows/macOS/Linux).
- Keep instructions reproducible and minimal.
