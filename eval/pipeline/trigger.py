"""Trigger — run eval subsets via subprocess with progress tracking."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

import structlog

from eval.pipeline_config import CORE_EVAL_DATASETS, FULL_EVAL_DATASETS

logger = structlog.get_logger(__name__)


@dataclass
class EvalRunResult:
    """Result of running a single eval dataset."""

    dataset_path: str
    exit_code: int
    passed: bool
    output: str


def run_eval_suite(
    suite: str = "core",
    verbose: bool = False,
    progress_callback: object | None = None,
) -> list[EvalRunResult]:
    """Run an eval suite (core or full) by invoking each dataset via subprocess.

    Args:
        suite: "core" for the default subset, "full" for all eval types.
        verbose: If True, pass --verbose flag to each eval run.
        progress_callback: Optional callable(index, total, dataset_path, result).

    Returns:
        List of EvalRunResult objects, one per dataset.
    """
    datasets = CORE_EVAL_DATASETS if suite == "core" else FULL_EVAL_DATASETS
    results: list[EvalRunResult] = []

    for i, dataset_path in enumerate(datasets):
        cmd = [sys.executable, "-m", "eval", "--dataset", dataset_path]
        if verbose:
            cmd.append("--verbose")

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout per eval
            )
            exit_code = proc.returncode
            output = proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            exit_code = 2
            output = f"Timeout: eval for {dataset_path} exceeded 600s"
            logger.warning("eval_timeout", dataset=dataset_path)
        except Exception as e:
            exit_code = 2
            output = f"Error running eval: {e}"
            logger.warning("eval_run_error", dataset=dataset_path, error=str(e))

        result = EvalRunResult(
            dataset_path=dataset_path,
            exit_code=exit_code,
            passed=exit_code == 0,
            output=output,
        )
        results.append(result)

        if progress_callback is not None and callable(progress_callback):
            progress_callback(i, len(datasets), dataset_path, result)

    return results
