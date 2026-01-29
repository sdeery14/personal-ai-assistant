"""
Evaluation configuration settings.

This module defines all configurable parameters for the evaluation framework,
loaded from environment variables with sensible defaults.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class EvalSettings(BaseSettings):
    """Configuration for the evaluation framework."""

    # OpenAI Configuration
    openai_api_key: str = Field(
        ...,
        description="OpenAI API key for assistant and judge calls",
    )
    openai_model: str = Field(
        default="gpt-4.1",
        description="Model for assistant responses",
    )

    # Judge Configuration
    eval_judge_model: str | None = Field(
        default=None,
        description="Model for judge evaluations (defaults to openai_model)",
    )

    # Threshold Configuration
    eval_pass_rate_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Minimum pass rate (0.0-1.0) for overall PASS",
    )
    eval_score_threshold: float = Field(
        default=3.5,
        ge=1.0,
        le=5.0,
        description="Minimum average score (1.0-5.0) for overall PASS",
    )

    # MLflow Configuration
    mlflow_tracking_uri: str = Field(
        default="http://localhost:5000",
        description="MLflow tracking server URI",
    )
    mlflow_experiment_name: str = Field(
        default="personal-ai-assistant-eval",
        description="MLflow experiment name for evaluation runs",
    )

    # Parallelization
    eval_max_workers: int = Field(
        default=1,
        ge=1,
        le=50,
        description="Number of parallel evaluation workers (default 1 for stability)",
    )

    # Assistant Configuration (reuse from Feature 001)
    max_tokens: int = Field(
        default=2000,
        ge=1,
        le=8000,
        description="Max tokens for assistant response",
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperature for assistant (0 for reproducibility)",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def judge_model(self) -> str:
        """Get the judge model, defaulting to assistant model if not set."""
        return self.eval_judge_model or self.openai_model


# Singleton instance for easy access
_settings: EvalSettings | None = None


def get_eval_settings() -> EvalSettings:
    """Get the evaluation settings singleton."""
    global _settings
    if _settings is None:
        _settings = EvalSettings()
    return _settings


def reset_settings() -> None:
    """Reset settings singleton (for testing)."""
    global _settings
    _settings = None
