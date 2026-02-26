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


# ---------------------------------------------------------------------------
# Per-eval-type MLflow metric/param column names
# ---------------------------------------------------------------------------
# Maps each eval type to the actual column names in mlflow.search_runs() output.
# Keys: pass_rate, error_cases, total_cases, average_score
# Column names include the "metrics." or "params." prefix matching the DataFrame.

EVAL_METRIC_NAMES: dict[str, dict[str, str]] = {
    "quality": {
        "pass_rate": "metrics.pass_rate",
        "average_score": "metrics.average_score",
        "total_cases": "metrics.total_cases",
        "error_cases": "metrics.error_cases",
    },
    "memory": {
        "pass_rate": "metrics.memory_recall_at_5",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.memory_error_cases",
    },
    "memory-write": {
        "pass_rate": "metrics.memory_write_judge_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.memory_write_error_cases",
    },
    "weather": {
        "pass_rate": "metrics.weather_success_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.weather_error_cases",
    },
    "graph-extraction": {
        "pass_rate": "metrics.graph_entity_recall",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.graph_error_cases",
    },
    "onboarding": {
        "pass_rate": "metrics.onboarding_quality_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.onboarding_error_cases",
    },
    "tone": {
        "pass_rate": "metrics.tone_quality_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.tone_error_cases",
    },
    "greeting": {
        "pass_rate": "metrics.greeting_quality_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.greeting_error_cases",
    },
    "routing": {
        "pass_rate": "metrics.routing_quality_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.routing_error_cases",
    },
    "memory-informed": {
        "pass_rate": "metrics.meminf_quality_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.meminf_error_cases",
    },
    "multi-cap": {
        "pass_rate": "metrics.mcap_quality_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.mcap_error_cases",
    },
    "notification-judgment": {
        "pass_rate": "metrics.notif_quality_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.notif_error_cases",
    },
    "error-recovery": {
        "pass_rate": "metrics.errrecov_quality_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.errrecov_error_cases",
    },
    "schedule-cron": {
        "pass_rate": "metrics.cron_quality_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.cron_error_cases",
    },
    "knowledge-connections": {
        "pass_rate": "metrics.kg_quality_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.kg_error_cases",
    },
    "contradiction": {
        "pass_rate": "metrics.contra_quality_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.contra_error_cases",
    },
    "long-conversation": {
        "pass_rate": "metrics.longconv_quality_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.longconv_error_cases",
    },
}

# Fallback for unknown eval types — matches the quality eval pattern.
_DEFAULT_METRIC_NAMES: dict[str, str] = {
    "pass_rate": "metrics.pass_rate",
    "average_score": "metrics.average_score",
    "total_cases": "metrics.total_cases",
    "error_cases": "metrics.error_cases",
}


def get_metric_names(eval_type: str) -> dict[str, str]:
    """Return the MLflow column-name mapping for a given eval type."""
    return EVAL_METRIC_NAMES.get(eval_type, _DEFAULT_METRIC_NAMES)
