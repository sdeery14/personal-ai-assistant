"""Pipeline configuration — eval subsets, thresholds, and experiment naming."""

from eval.config import get_eval_settings

# ---------------------------------------------------------------------------
# Eval dataset paths (relative to repo root)
# ---------------------------------------------------------------------------

CORE_EVAL_DATASETS: list[str] = [
    "eval/golden_dataset.json",
    "eval/security_golden_dataset.json",
    "eval/tone_golden_dataset.json",
    "eval/routing_golden_dataset.json",
    "eval/returning_greeting_golden_dataset.json",
]

FULL_EVAL_DATASETS: list[str] = [
    "eval/golden_dataset.json",
    "eval/security_golden_dataset.json",
    "eval/tone_golden_dataset.json",
    "eval/routing_golden_dataset.json",
    "eval/returning_greeting_golden_dataset.json",
    "eval/memory_golden_dataset.json",
    "eval/memory_write_golden_dataset.json",
    "eval/memory_informed_golden_dataset.json",
    "eval/weather_golden_dataset.json",
    "eval/graph_extraction_golden_dataset.json",
    "eval/onboarding_golden_dataset.json",
    "eval/multi_cap_golden_dataset.json",
    "eval/notification_judgment_golden_dataset.json",
    "eval/error_recovery_golden_dataset.json",
    "eval/schedule_cron_golden_dataset.json",
    "eval/knowledge_connections_golden_dataset.json",
    "eval/contradiction_handling_golden_dataset.json",
    "eval/long_conversation_golden_dataset.json",
    "eval/proactive_golden_dataset.json",
]

# ---------------------------------------------------------------------------
# Experiment suffix → eval type mapping
# ---------------------------------------------------------------------------

EXPERIMENT_SUFFIXES: dict[str, str] = {
    "": "quality",
    "-memory": "memory",
    "-memory-write": "memory-write",
    "-weather": "weather",
    "-graph-extraction": "graph-extraction",
    "-onboarding": "onboarding",
    "-tone": "tone",
    "-greeting": "greeting",
    "-routing": "routing",
    "-memory-informed": "memory-informed",
    "-multi-cap": "multi-cap",
    "-notification-judgment": "notification-judgment",
    "-error-recovery": "error-recovery",
    "-schedule-cron": "schedule-cron",
    "-knowledge-connections": "knowledge-connections",
    "-contradiction": "contradiction",
    "-long-conversation": "long-conversation",
}

# ---------------------------------------------------------------------------
# Per-eval-type pass rate thresholds
# ---------------------------------------------------------------------------

DEFAULT_PASS_RATE_THRESHOLD: float = 0.80

EVAL_THRESHOLDS: dict[str, float] = {
    # All eval types default to 0.80; override specific ones here if needed.
}


def get_threshold(eval_type: str) -> float:
    """Return the pass rate threshold for a given eval type."""
    return EVAL_THRESHOLDS.get(eval_type, DEFAULT_PASS_RATE_THRESHOLD)


def get_base_experiment_name() -> str:
    """Return the configured base MLflow experiment name."""
    return get_eval_settings().mlflow_experiment_name


# ---------------------------------------------------------------------------
# Per-eval-type artifact filenames (logged by eval runners)
# ---------------------------------------------------------------------------

ARTIFACT_FILENAMES: dict[str, str] = {
    "quality": "eval_results.json",
    "memory": "memory_eval_results.json",
    "memory-write": "memory_write_eval_results.json",
    "weather": "weather_eval_results.json",
    "graph-extraction": "graph_extraction_eval_results.json",
    "onboarding": "onboarding_eval_results.json",
    "tone": "tone_eval_results.json",
    "greeting": "greeting_eval_results.json",
    "routing": "routing_eval_results.json",
    "memory-informed": "memory_informed_eval_results.json",
    "multi-cap": "multi_cap_eval_results.json",
    "notification-judgment": "notification_judgment_eval_results.json",
    "error-recovery": "error_recovery_eval_results.json",
    "schedule-cron": "schedule_cron_eval_results.json",
    "knowledge-connections": "knowledge_connections_eval_results.json",
    "contradiction": "contradiction_handling_eval_results.json",
    "long-conversation": "long_conversation_eval_results.json",
}


def get_artifact_filename(eval_type: str) -> str | None:
    """Return the artifact filename for a given eval type, or None if unknown."""
    return ARTIFACT_FILENAMES.get(eval_type)
