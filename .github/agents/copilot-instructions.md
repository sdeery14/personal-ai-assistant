# personal-ai-assistant Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-28

## Active Technologies
- Python 3.11 + mlflow==3.8.1, openai-agents (existing), pydantic>=2.10.0 (002-judge-eval-framework)
- PostgreSQL (MLflow backend), MinIO (S3-compatible artifacts) (002-judge-eval-framework)
- [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION] + [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION] (003-security-guardrails)
- [if applicable, e.g., PostgreSQL, CoreData, files or N/A] (003-security-guardrails)

- Python 3.11 + FastAPI 0.109+, OpenAI Agents SDK (latest), Pydantic 2.x, structlog (001-streaming-chat-api)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11: Follow standard conventions

## Recent Changes
- 003-security-guardrails: Added [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION] + [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]
- 002-judge-eval-framework: Added Python 3.11 + mlflow==3.8.1, openai-agents (existing), pydantic>=2.10.0

- 001-streaming-chat-api: Added Python 3.11 + FastAPI 0.109+, OpenAI Agents SDK (latest), Pydantic 2.x, structlog

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
