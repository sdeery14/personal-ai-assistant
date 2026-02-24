"""Promotion gating — check eval thresholds before allowing alias promotion."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from mlflow import MlflowClient

from eval.pipeline.aggregator import get_eval_experiments, get_trend_points
from eval.pipeline.models import (
    AuditRecord,
    PromotionEvalCheck,
    PromotionResult,
)
from eval.pipeline_config import get_threshold

logger = structlog.get_logger(__name__)


def check_promotion_gate(
    prompt_name: str,
    from_alias: str = "experiment",
    to_alias: str = "production",
    version: int | None = None,
) -> PromotionResult:
    """Check all eval types against minimum thresholds before allowing promotion.

    Args:
        prompt_name: Name of the prompt to promote.
        from_alias: Source alias.
        to_alias: Target alias.
        version: Specific version to promote. If None, uses current version.

    Returns:
        PromotionResult with per-eval-type checks and overall verdict.
    """
    from src.services.prompt_service import load_prompt_version

    # Resolve the version being promoted
    if version is None:
        info = load_prompt_version(prompt_name, alias=from_alias)
        version = info.version

    experiments = get_eval_experiments()
    eval_checks: list[PromotionEvalCheck] = []
    justifying_run_ids: list[str] = []
    blocking_evals: list[str] = []

    for exp_name, eval_type in experiments:
        points = get_trend_points(exp_name, eval_type, limit=10)
        complete_points = [p for p in points if p.eval_status == "complete"]

        if not complete_points:
            # Skip eval types with no complete runs (log warning)
            logger.warning(
                "promotion_gate_skip_no_data",
                eval_type=eval_type,
                prompt_name=prompt_name,
            )
            continue

        latest = complete_points[-1]
        threshold = get_threshold(eval_type)
        passed = latest.pass_rate >= threshold

        eval_checks.append(
            PromotionEvalCheck(
                eval_type=eval_type,
                pass_rate=latest.pass_rate,
                threshold=threshold,
                passed=passed,
                run_id=latest.run_id,
            )
        )

        justifying_run_ids.append(latest.run_id)

        if not passed:
            blocking_evals.append(eval_type)

    allowed = len(blocking_evals) == 0

    return PromotionResult(
        allowed=allowed,
        prompt_name=prompt_name,
        from_alias=from_alias,
        to_alias=to_alias,
        version=version,
        eval_results=eval_checks,
        blocking_evals=blocking_evals,
        justifying_run_ids=justifying_run_ids,
    )


def execute_promotion(
    prompt_name: str,
    to_alias: str,
    version: int,
    actor: str,
    justifying_run_ids: list[str],
    from_version: int | None = None,
) -> AuditRecord:
    """Execute the alias promotion and log audit tags.

    Args:
        prompt_name: Name of the prompt.
        to_alias: Target alias to point.
        version: Version number to promote to.
        actor: Who performed the action.
        justifying_run_ids: MLflow run IDs that justify this promotion.
        from_version: Previous version (for audit record).

    Returns:
        AuditRecord of the promotion action.
    """
    from src.services.prompt_service import load_prompt_version, set_alias

    # Get the current version before promotion (for audit trail)
    if from_version is None:
        try:
            current = load_prompt_version(prompt_name, alias=to_alias)
            from_version = current.version
        except Exception:
            from_version = 0

    # Execute the alias swap
    set_alias(prompt_name, to_alias, version)

    # Create audit record
    record = AuditRecord(
        action="promote",
        prompt_name=prompt_name,
        from_version=from_version,
        to_version=version,
        alias=to_alias,
        timestamp=datetime.now(timezone.utc),
        actor=actor,
        reason=f"All eval types pass thresholds. Promoted to @{to_alias}.",
        justifying_run_ids=justifying_run_ids,
    )

    # Log audit tags on justifying runs
    _log_audit_tags(record)

    return record


def _log_audit_tags(record: AuditRecord) -> None:
    """Write audit tags to each justifying MLflow run."""
    client = MlflowClient()
    tags = record.to_tags()

    for run_id in record.justifying_run_ids:
        try:
            for key, value in tags.items():
                client.set_tag(run_id, key, value)
            logger.info("audit_tag_logged", run_id=run_id, action=record.action)
        except Exception:
            logger.warning(
                "audit_tag_failed",
                run_id=run_id,
                action=record.action,
            )
