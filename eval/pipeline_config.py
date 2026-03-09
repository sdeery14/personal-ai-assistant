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
]

# ---------------------------------------------------------------------------
# Experiment suffix → eval type mapping
# ---------------------------------------------------------------------------

EXPERIMENT_SUFFIXES: dict[str, str] = {
    "": "quality",
    "-security": "security",
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
# Per-eval-type primary scorer name (assessment name on traces)
# ---------------------------------------------------------------------------

EVAL_PRIMARY_SCORER: dict[str, str] = {
    "quality": "quality",
    "security": "quality",
    "tone": "tone_quality",
    "greeting": "greeting_quality",
    "routing": "routing_quality",
    "notification-judgment": "notification_quality",
    "error-recovery": "error_recovery_quality",
    "schedule-cron": "schedule_quality",
    "knowledge-connections": "knowledge_connections_quality",
    "contradiction": "contradiction_quality",
    "memory-informed": "memory_informed_quality",
    "multi-cap": "multi_cap_quality",
    "long-conversation": "long_conversation_quality",
    "onboarding": "onboarding_quality",
    "weather": "weather_behavior_scorer",
    "graph-extraction": "entity_recall_scorer",
    "memory-write": "memory_write_quality",
    "memory": "memory_retrieval",
}


def get_primary_scorer(eval_type: str) -> str | None:
    """Return the primary assessment name for a given eval type, or None if unknown."""
    return EVAL_PRIMARY_SCORER.get(eval_type)


# ---------------------------------------------------------------------------
# Session-trace eval types (multi-turn conversations grouped by session)
# ---------------------------------------------------------------------------

EVAL_SESSION_TYPES: frozenset[str] = frozenset({
    "onboarding",
    "contradiction",
    "memory-informed",
    "multi-cap",
    "long-conversation",
})


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
        "overall_passed": "metrics.overall_passed",
    },
    "security": {
        "pass_rate": "metrics.block_rate",
        "average_score": "metrics.average_score",
        "total_cases": "metrics.total_cases",
        "error_cases": "metrics.error_cases",
        "overall_passed": "metrics.security_gate_passed",
    },
    "memory": {
        "pass_rate": "metrics.memory_recall_at_5",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.memory_error_cases",
        "overall_passed": "metrics.memory_overall_passed",
    },
    "memory-write": {
        "pass_rate": "metrics.memory_write_judge_pass_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.memory_write_error_cases",
        "overall_passed": "metrics.memory_write_overall_passed",
    },
    "weather": {
        "pass_rate": "metrics.weather_success_rate",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.weather_error_cases",
        "overall_passed": "metrics.weather_overall_passed",
    },
    "graph-extraction": {
        "pass_rate": "metrics.graph_entity_recall",
        "average_score": "",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.graph_error_cases",
        "overall_passed": "metrics.graph_overall_passed",
    },
    "onboarding": {
        "pass_rate": "metrics.onboarding_quality_pass_rate",
        "average_score": "metrics.onboarding_average_score",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.onboarding_error_cases",
        "overall_passed": "metrics.onboarding_overall_passed",
    },
    "tone": {
        "pass_rate": "metrics.tone_quality_pass_rate",
        "average_score": "metrics.tone_average_score",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.tone_error_cases",
        "overall_passed": "metrics.tone_overall_passed",
    },
    "greeting": {
        "pass_rate": "metrics.greeting_quality_pass_rate",
        "average_score": "metrics.greeting_average_score",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.greeting_error_cases",
        "overall_passed": "metrics.greeting_overall_passed",
    },
    "routing": {
        "pass_rate": "metrics.routing_quality_pass_rate",
        "average_score": "metrics.routing_average_score",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.routing_error_cases",
        "overall_passed": "metrics.routing_overall_passed",
    },
    "memory-informed": {
        "pass_rate": "metrics.meminf_quality_pass_rate",
        "average_score": "metrics.meminf_average_score",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.meminf_error_cases",
        "overall_passed": "metrics.meminf_overall_passed",
    },
    "multi-cap": {
        "pass_rate": "metrics.mcap_quality_pass_rate",
        "average_score": "metrics.mcap_average_score",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.mcap_error_cases",
        "overall_passed": "metrics.mcap_overall_passed",
    },
    "notification-judgment": {
        "pass_rate": "metrics.notif_quality_pass_rate",
        "average_score": "metrics.notif_average_score",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.notif_error_cases",
        "overall_passed": "metrics.notif_overall_passed",
    },
    "error-recovery": {
        "pass_rate": "metrics.errrecov_quality_pass_rate",
        "average_score": "metrics.errrecov_average_score",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.errrecov_error_cases",
        "overall_passed": "metrics.errrecov_overall_passed",
    },
    "schedule-cron": {
        "pass_rate": "metrics.cron_quality_pass_rate",
        "average_score": "metrics.cron_average_score",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.cron_error_cases",
        "overall_passed": "metrics.cron_overall_passed",
    },
    "knowledge-connections": {
        "pass_rate": "metrics.kg_quality_pass_rate",
        "average_score": "metrics.kg_average_score",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.kg_error_cases",
        "overall_passed": "metrics.kg_overall_passed",
    },
    "contradiction": {
        "pass_rate": "metrics.contra_quality_pass_rate",
        "average_score": "metrics.contra_average_score",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.contra_error_cases",
        "overall_passed": "metrics.contra_overall_passed",
    },
    "long-conversation": {
        "pass_rate": "metrics.longconv_quality_pass_rate",
        "average_score": "metrics.longconv_average_score",
        "total_cases": "params.total_cases",
        "error_cases": "metrics.longconv_error_cases",
        "overall_passed": "metrics.longconv_overall_passed",
    },
}

# Fallback for unknown eval types — matches the quality eval pattern.
_DEFAULT_METRIC_NAMES: dict[str, str] = {
    "pass_rate": "metrics.pass_rate",
    "average_score": "metrics.average_score",
    "total_cases": "metrics.total_cases",
    "error_cases": "metrics.error_cases",
    "overall_passed": "metrics.overall_passed",
}


def get_metric_names(eval_type: str) -> dict[str, str]:
    """Return the MLflow column-name mapping for a given eval type."""
    return EVAL_METRIC_NAMES.get(eval_type, _DEFAULT_METRIC_NAMES)


# ---------------------------------------------------------------------------
# Per-eval-type human-readable metric descriptions (for UI tooltips)
# ---------------------------------------------------------------------------

_DEFAULT_PASS_RATE_DESC = "% of cases scoring >= 4 on a 1-5 LLM judge scale."
_DEFAULT_AVG_SCORE_DESC = "Mean LLM judge score (1-5 scale) across all cases."

EVAL_METRIC_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "security": {
        "pass_rate": "Block rate: % of adversarial inputs correctly blocked by guardrails.",
        "average_score": "",
    },
    "memory": {
        "pass_rate": "Recall@5: fraction of expected memories found in top-5 retrieval results.",
        "average_score": "",
    },
    "memory-write": {
        "pass_rate": "% of cases where memory_write_quality judge scores >= 4 (1-5 scale).",
        "average_score": "",
    },
    "weather": {
        "pass_rate": "% of cases passing the weather_behavior_scorer (correct tool usage).",
        "average_score": "",
    },
    "graph-extraction": {
        "pass_rate": "Entity recall: fraction of expected entities extracted by the agent.",
        "average_score": "",
    },
}


def get_metric_descriptions(eval_type: str) -> dict[str, str]:
    """Return pass_rate and average_score descriptions for the given eval type."""
    custom = EVAL_METRIC_DESCRIPTIONS.get(eval_type)
    if custom:
        return {
            "pass_rate": custom["pass_rate"],
            "average_score": custom["average_score"],
        }
    return {
        "pass_rate": _DEFAULT_PASS_RATE_DESC,
        "average_score": _DEFAULT_AVG_SCORE_DESC,
    }
