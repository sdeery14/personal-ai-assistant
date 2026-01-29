"""
Evaluation Framework for Personal AI Assistant.

This package provides LLM-as-a-judge evaluation capabilities using MLflow GenAI.
It evaluates the Feature 001 assistant against a golden dataset and logs results
to MLflow for tracking, visualization, and regression gating.

Usage:
    python -m eval [OPTIONS]

Modules:
    config      - Evaluation configuration (thresholds, models, env vars)
    models      - Pydantic data models (TestCase, EvalResult, etc.)
    dataset     - Golden dataset loading and validation
    assistant   - Sync wrapper for Feature 001 ChatService
    judge       - LLM judge definition using mlflow.genai.judges
    runner      - Evaluation orchestrator

See also:
    - specs/002-judge-eval-framework/quickstart.md for setup guide
    - docker/docker-compose.mlflow.yml for MLflow stack
"""

__version__ = "0.1.0"
