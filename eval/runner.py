"""
Evaluation runner orchestrator.

This module orchestrates the complete evaluation flow:
1. Load and validate the golden dataset
2. Invoke the assistant for each test case
3. Score responses using the LLM judge
4. Aggregate metrics and compute pass/fail
5. Log results to MLflow

Uses mlflow.genai.evaluate() for standardized evaluation with automatic
metric aggregation and artifact logging.
"""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mlflow
import pandas as pd
from mlflow.genai import evaluate as genai_evaluate

from eval.assistant import get_response
from eval.config import EvalSettings, get_eval_settings
from eval.dataset import DatasetError, load_dataset
from eval.judge import create_quality_judge, score_to_label, score_to_passed
from eval.models import EvalResult, EvalRunMetrics, GoldenDataset


@dataclass
class EvaluationResult:
    """Complete results from an evaluation run."""

    metrics: EvalRunMetrics
    results: list[EvalResult]
    mlflow_run_id: str | None
    dataset_version: str
    error: str | None = None


def run_evaluation(
    dataset_path: str | Path = "eval/golden_dataset.json",
    model: str | None = None,
    judge_model: str | None = None,
    pass_threshold: float | None = None,
    score_threshold: float | None = None,
    verbose: bool = False,
    dry_run: bool = False,
    max_workers: int | None = None,
) -> EvaluationResult:
    """
    Run the full evaluation suite.

    Args:
        dataset_path: Path to the golden dataset JSON file.
        model: Override for assistant model (defaults to OPENAI_MODEL).
        judge_model: Override for judge model (defaults to EVAL_JUDGE_MODEL).
        pass_threshold: Override for pass rate threshold (defaults to EVAL_PASS_RATE_THRESHOLD).
        score_threshold: Override for score threshold (defaults to EVAL_SCORE_THRESHOLD).
        verbose: If True, print per-case details during evaluation.
        dry_run: If True, validate dataset only without running evaluation.
        max_workers: Number of parallel evaluation workers.

    Returns:
        EvaluationResult with metrics, per-case results, and MLflow run ID.

    Raises:
        DatasetError: If the dataset cannot be loaded or is invalid.
    """
    settings = get_eval_settings()

    # Apply overrides
    actual_model = model or settings.openai_model
    actual_judge_model = judge_model or settings.judge_model
    actual_pass_threshold = (
        pass_threshold
        if pass_threshold is not None
        else settings.eval_pass_rate_threshold
    )
    actual_score_threshold = (
        score_threshold
        if score_threshold is not None
        else settings.eval_score_threshold
    )
    actual_max_workers = max_workers or settings.eval_max_workers

    # Set parallelization environment variable
    os.environ["MLFLOW_GENAI_EVAL_MAX_WORKERS"] = str(actual_max_workers)

    # Load dataset
    dataset = load_dataset(dataset_path)

    if verbose:
        print(f"📂 Loaded dataset v{dataset.version} with {len(dataset.cases)} cases")

    # Dry run: just validate and return
    if dry_run:
        return EvaluationResult(
            metrics=EvalRunMetrics(
                total_cases=len(dataset.cases),
                passed_cases=0,
                failed_cases=0,
                error_cases=0,
                pass_rate=0.0,
                average_score=1.0,
                overall_passed=False,
            ),
            results=[],
            mlflow_run_id=None,
            dataset_version=dataset.version,
        )

    # Set up MLflow
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment_name)

    # Prepare data for mlflow.genai.evaluate()
    eval_data = _prepare_eval_data(dataset)

    # Capture API key in closure for MLflow predict_fn
    # MLflow doesn't pass environment variables, so we must explicitly capture them
    api_key = settings.openai_api_key

    # Create predict function that wraps assistant
    # Note: Parameter name must match the key in inputs dict
    def predict_fn(question: str) -> str:
        """Predict function for mlflow.genai.evaluate."""
        # CRITICAL: Set environment variable first, before any OpenAI SDK initialization
        # MLflow serializes this function and doesn't preserve the parent environment
        import os

        os.environ["OPENAI_API_KEY"] = api_key

        try:
            response = get_response(question, model=actual_model, api_key=api_key)
            return response
        except Exception as e:
            # Return error message instead of raising - allows evaluation to continue
            return f"[ERROR: {type(e).__name__}: {str(e)}]"

    # Create judge
    quality_judge = create_quality_judge()

    # Run evaluation with MLflow
    with mlflow.start_run() as run:
        run_id = run.info.run_id

        # Log parameters
        mlflow.log_params(
            {
                "assistant_model": actual_model,
                "judge_model": actual_judge_model,
                "temperature": settings.temperature,
                "max_tokens": settings.max_tokens,
                "dataset_version": dataset.version,
                "pass_rate_threshold": actual_pass_threshold,
                "score_threshold": actual_score_threshold,
                "total_cases": len(dataset.cases),
            }
        )

        # Run evaluation
        start_time = time.perf_counter()
        eval_results = genai_evaluate(
            data=eval_data,
            predict_fn=predict_fn,
            scorers=[quality_judge],
        )
        eval_duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Process results
        results, metrics = _process_eval_results(
            eval_results=eval_results,
            dataset=dataset,
            pass_threshold=actual_pass_threshold,
            score_threshold=actual_score_threshold,
            verbose=verbose,
        )

        # Log metrics
        mlflow.log_metrics(
            {
                "total_cases": metrics.total_cases,
                "passed_cases": metrics.passed_cases,
                "failed_cases": metrics.failed_cases,
                "error_cases": metrics.error_cases,
                "pass_rate": metrics.pass_rate,
                "average_score": metrics.average_score,
                "overall_passed": 1 if metrics.overall_passed else 0,
                "eval_duration_ms": eval_duration_ms,
            }
        )

        # Log per-case results as artifact
        results_json = [r.model_dump() for r in results]
        results_path = Path("eval_results.json")
        with open(results_path, "w") as f:
            json.dump(results_json, f, indent=2, default=str)
        mlflow.log_artifact(str(results_path))
        results_path.unlink()  # Clean up temp file

        # Log dataset as artifact for reproducibility
        mlflow.log_artifact(str(dataset_path))

    return EvaluationResult(
        metrics=metrics,
        results=results,
        mlflow_run_id=run_id,
        dataset_version=dataset.version,
    )


def _prepare_eval_data(dataset: GoldenDataset) -> list[dict[str, Any]]:
    """
    Prepare dataset for mlflow.genai.evaluate().

    Converts GoldenDataset to the format expected by MLflow 3.x:
    - inputs: Dictionary with 'question' key
    - expectations: Dictionary with 'rubric' key
    """
    return [
        {
            "inputs": {"question": case.user_prompt},
            "expectations": {"rubric": case.rubric},
            "_case_id": case.id,  # Keep for result mapping
        }
        for case in dataset.cases
    ]


def _process_eval_results(
    eval_results: Any,
    dataset: GoldenDataset,
    pass_threshold: float,
    score_threshold: float,
    verbose: bool = False,
) -> tuple[list[EvalResult], EvalRunMetrics]:
    """
    Process MLflow evaluation results into our data models.

    Args:
        eval_results: Results from mlflow.genai.evaluate()
        dataset: Original dataset for case mapping
        pass_threshold: Pass rate threshold for overall decision
        score_threshold: Average score threshold for overall decision
        verbose: Print per-case details

    Returns:
        Tuple of (list of EvalResult, EvalRunMetrics)
    """
    results: list[EvalResult] = []
    total_score = 0
    passed_count = 0
    failed_count = 0
    error_count = 0

    # Get results DataFrame from MLflow
    # MLflow 3.8.1 uses "eval_results" table name
    try:
        results_df = eval_results.tables["eval_results_table"]
    except (KeyError, AttributeError):
        # Fallback: MLflow 3.8.1 actually uses "eval_results" (without _table suffix)
        try:
            results_df = eval_results.tables["eval_results"]
        except (KeyError, AttributeError) as e:
            # Last resort: try to find any available table
            available_tables = (
                list(eval_results.tables.keys())
                if hasattr(eval_results, "tables")
                else []
            )
            if available_tables:
                results_df = eval_results.tables[available_tables[0]]
            else:
                raise DatasetError(
                    f"No evaluation results table found in MLflow output. "
                    f"Available tables: {available_tables}. Error: {e}"
                )

    for idx, case in enumerate(dataset.cases):
        try:
            # Get row for this case
            row = results_df.iloc[idx]

            # Extract score from quality judge output
            # MLflow 3.8.1 uses 'quality/value' column for judge scores
            score_value = row.get("quality/value")
            if pd.isna(score_value):
                score = 3  # Default if missing
            else:
                # Handle dict or string format
                if isinstance(score_value, dict):
                    score = int(score_value.get("result", "3"))
                else:
                    score = int(score_value)

            # Get response from trace
            response_value = row.get("response", "")
            if isinstance(response_value, dict):
                response = response_value.get("content", str(response_value))
            else:
                response = str(response_value)

            # Get justification from assessments or quality rationale
            justification = "No justification provided"
            assessments = row.get("assessments", [])
            if isinstance(assessments, list) and len(assessments) > 0:
                for assessment in assessments:
                    if (
                        isinstance(assessment, dict)
                        and assessment.get("name") == "quality"
                    ):
                        justification = assessment.get("rationale", justification)
                        break

            passed = score_to_passed(score)

            result = EvalResult(
                case_id=case.id,
                user_prompt=case.user_prompt,
                assistant_response=str(response),
                score=score,
                passed=passed,
                justification=str(justification),
                duration_ms=1000,  # Placeholder; MLflow doesn't provide per-case timing
            )

            results.append(result)
            total_score += score

            if passed:
                passed_count += 1
            else:
                failed_count += 1

            if verbose:
                status = "✅ PASS" if passed else "❌ FAIL"
                label = score_to_label(score)
                print(f"  {case.id}: {status} (Score: {score}/5 - {label})")

        except Exception as e:
            # Handle errors for individual cases
            error_count += 1
            results.append(
                EvalResult(
                    case_id=case.id,
                    user_prompt=case.user_prompt,
                    assistant_response="",
                    score=1,
                    passed=False,
                    justification=f"Error: {str(e)}",
                    duration_ms=1,  # Minimum valid duration
                    error=str(e),
                )
            )

            if verbose:
                print(f"  {case.id}: ⚠️ ERROR - {str(e)}")

    # Calculate aggregate metrics
    evaluated_cases = len(dataset.cases) - error_count
    pass_rate = passed_count / evaluated_cases if evaluated_cases > 0 else 0.0
    average_score = total_score / evaluated_cases if evaluated_cases > 0 else 1.0

    overall_passed = pass_rate >= pass_threshold and average_score >= score_threshold

    metrics = EvalRunMetrics(
        total_cases=len(dataset.cases),
        passed_cases=passed_count,
        failed_cases=failed_count,
        error_cases=error_count,
        pass_rate=pass_rate,
        average_score=average_score,
        overall_passed=overall_passed,
    )

    return results, metrics


def format_summary(result: EvaluationResult, settings: EvalSettings) -> str:
    """
    Format evaluation results as a summary string.

    Args:
        result: EvaluationResult from run_evaluation()
        settings: EvalSettings for threshold display

    Returns:
        Formatted summary string for console output.
    """
    m = result.metrics
    lines = [
        "",
        "=" * 60,
        "EVALUATION SUMMARY",
        "=" * 60,
        f"Dataset Version: {result.dataset_version}",
        f"MLflow Run ID:   {result.mlflow_run_id or 'N/A'}",
        "",
        f"Total Cases:     {m.total_cases}",
        f"Passed:          {m.passed_cases} ({m.pass_rate:.1%})",
        f"Failed:          {m.failed_cases}",
        f"Errors:          {m.error_cases}",
        f"Average Score:   {m.average_score:.2f}/5.0",
        "",
        f"Pass Rate Threshold:  {settings.eval_pass_rate_threshold:.0%} (actual: {m.pass_rate:.1%})",
        f"Score Threshold:      {settings.eval_score_threshold:.1f} (actual: {m.average_score:.2f})",
        "",
    ]

    if m.overall_passed:
        lines.append("🎉 OVERALL: PASS")
    else:
        lines.append("❌ OVERALL: FAIL")
        # Add failure reasons
        reasons = []
        if m.pass_rate < settings.eval_pass_rate_threshold:
            reasons.append(
                f"Pass rate {m.pass_rate:.1%} < {settings.eval_pass_rate_threshold:.0%}"
            )
        if m.average_score < settings.eval_score_threshold:
            reasons.append(
                f"Average score {m.average_score:.2f} < {settings.eval_score_threshold:.1f}"
            )
        if reasons:
            lines.append(f"   Reasons: {'; '.join(reasons)}")

    lines.append("=" * 60)

    return "\n".join(lines)
