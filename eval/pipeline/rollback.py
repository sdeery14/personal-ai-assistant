"""Rollback — revert prompt alias to previous version with audit logging."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from mlflow import MlflowClient

from eval.pipeline.aggregator import get_eval_experiments, get_trend_points
from eval.pipeline.models import AuditRecord

logger = structlog.get_logger(__name__)


def find_previous_version(
    prompt_name: str,
    alias: str = "production",
) -> int | None:
    """Find the previous version of a prompt by examining eval run history.

    Searches eval runs for the most recent baseline run that used a different
    version of the specified prompt, returning that version number.

    Args:
        prompt_name: Name of the prompt.
        alias: Alias being rolled back.

    Returns:
        Previous version number, or None if no previous version found.
    """
    from src.services.prompt_service import load_prompt_version

    # Get the current version
    try:
        current_info = load_prompt_version(prompt_name, alias=alias)
        current_version = current_info.version
    except Exception:
        logger.warning("rollback_load_current_failed", prompt_name=prompt_name)
        return None

    if current_version <= 1:
        return None

    # Search eval runs for runs that used a different version
    experiments = get_eval_experiments()

    for exp_name, eval_type in experiments:
        points = get_trend_points(exp_name, eval_type, limit=50)
        complete_points = [p for p in points if p.eval_status == "complete"]

        # Look backwards through runs for a different version
        for point in reversed(complete_points):
            version_str = point.prompt_versions.get(prompt_name)
            if version_str is not None:
                # Parse version number from "vN" format
                try:
                    version_num = int(version_str.lstrip("v"))
                except (ValueError, AttributeError):
                    continue

                if version_num != current_version:
                    return version_num

    # Fallback: previous version is current - 1
    return current_version - 1


def execute_rollback(
    prompt_name: str,
    alias: str,
    previous_version: int,
    reason: str,
    actor: str,
) -> AuditRecord:
    """Execute the alias rollback and log audit tags.

    Args:
        prompt_name: Name of the prompt.
        alias: Alias to roll back.
        previous_version: Version to revert to.
        reason: Reason for the rollback.
        actor: Who performed the action.

    Returns:
        AuditRecord of the rollback action.
    """
    from src.services.prompt_service import load_prompt_version, set_alias

    # Get current version for audit record
    try:
        current = load_prompt_version(prompt_name, alias=alias)
        current_version = current.version
    except Exception:
        current_version = 0

    # Execute alias swap
    set_alias(prompt_name, alias, previous_version)

    # Find the most recent eval run for audit tag logging
    justifying_run_ids = _find_recent_run_ids()

    # Create audit record
    record = AuditRecord(
        action="rollback",
        prompt_name=prompt_name,
        from_version=current_version,
        to_version=previous_version,
        alias=alias,
        timestamp=datetime.now(timezone.utc),
        actor=actor,
        reason=reason,
        justifying_run_ids=justifying_run_ids,
    )

    # Log audit tags
    _log_audit_tags(record)

    return record


def _find_recent_run_ids(limit: int = 1) -> list[str]:
    """Find the most recent eval run IDs for audit tagging."""
    experiments = get_eval_experiments()

    for exp_name, eval_type in experiments:
        points = get_trend_points(exp_name, eval_type, limit=limit)
        if points:
            return [points[-1].run_id]

    return []


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
