# Copilot Instructions (Repository)

## Docker Deployment (IMPORTANT)

- **ALWAYS assume services run in Docker containers, NOT locally via `uv run uvicorn` or similar commands.**
- The Chat API runs in Docker via: `docker compose -f docker/docker-compose.api.yml up -d`
- MLflow runs in Docker via: `docker compose -f docker/docker-compose.mlflow.yml up -d`
- When making code changes, rebuild containers: `docker compose -f docker/docker-compose.api.yml up -d --build`
- Use `--env-file .env` flag with docker compose to load environment variables
- Check container status with: `docker ps`
- View container logs with: `docker logs chat-api` or `docker logs mlflow-server`

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

## General

- Prefer cross-platform commands (Windows/macOS/Linux).
- Keep instructions reproducible and minimal.
