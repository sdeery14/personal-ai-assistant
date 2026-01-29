"""
CLI entry point for the evaluation framework.

Usage:
    python -m eval [OPTIONS]

Run the LLM-as-a-judge evaluation suite against the Feature 001 assistant.
Results are logged to MLflow and displayed in the console.

Exit Codes:
    0 - PASS: All thresholds met
    1 - FAIL: Thresholds not met
    2 - ERROR: Evaluation failed to run
"""

import argparse
import sys
from pathlib import Path

from eval.config import get_eval_settings, reset_settings
from eval.dataset import DatasetError
from eval.runner import EvaluationResult, format_summary, run_evaluation


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="python -m eval",
        description="Run LLM-as-a-judge evaluation for the Personal AI Assistant.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with defaults
    python -m eval

    # Run with custom dataset
    python -m eval --dataset path/to/dataset.json

    # Validate dataset without running evaluation
    python -m eval --dry-run

    # Run with verbose output (show per-case details)
    python -m eval --verbose

    # Run with custom thresholds
    python -m eval --pass-threshold 0.90 --score-threshold 4.0

Exit Codes:
    0 - PASS: All thresholds met
    1 - FAIL: Thresholds not met
    2 - ERROR: Evaluation failed to run

MLflow UI:
    After running evaluation, view results at http://localhost:5000
    """,
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default="eval/golden_dataset.json",
        help="Path to golden dataset JSON file (default: eval/golden_dataset.json)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Assistant model to use (default: OPENAI_MODEL env var)",
    )

    parser.add_argument(
        "--judge-model",
        type=str,
        default=None,
        help="Judge model to use (default: EVAL_JUDGE_MODEL env var or --model)",
    )

    parser.add_argument(
        "--pass-threshold",
        type=float,
        default=None,
        help="Minimum pass rate (0.0-1.0) for overall PASS (default: 0.80)",
    )

    parser.add_argument(
        "--score-threshold",
        type=float,
        default=None,
        help="Minimum average score (1.0-5.0) for overall PASS (default: 3.5)",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel evaluation workers (default: 10)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show per-case details during evaluation",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate dataset without running evaluation",
    )

    return parser.parse_args()


def main() -> int:
    """
    Main entry point for CLI.

    Returns:
        Exit code: 0 (PASS), 1 (FAIL), or 2 (ERROR).
    """
    # Fix Windows console encoding for emojis
    import io

    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

    args = parse_args()

    # Reset settings to pick up latest env vars
    reset_settings()

    try:
        settings = get_eval_settings()
    except Exception as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        print("   Make sure OPENAI_API_KEY is set.", file=sys.stderr)
        return 2

    # Print header
    print()
    print("=" * 60)
    print("PERSONAL AI ASSISTANT - EVALUATION FRAMEWORK")
    print("=" * 60)
    print()

    # Show configuration
    if args.verbose or args.dry_run:
        print("Configuration:")
        print(f"  Dataset:         {args.dataset}")
        print(f"  Model:           {args.model or settings.openai_model}")
        print(f"  Judge Model:     {args.judge_model or settings.judge_model}")
        print(
            f"  Pass Threshold:  {args.pass_threshold or settings.eval_pass_rate_threshold:.0%}"
        )
        print(
            f"  Score Threshold: {args.score_threshold or settings.eval_score_threshold:.1f}"
        )
        print(f"  Workers:         {args.workers or settings.eval_max_workers}")
        print()

    # Validate dataset path
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}", file=sys.stderr)
        return 2

    try:
        if args.dry_run:
            # Dry run mode: validate only
            print("🔍 Validating dataset (dry run)...")
            result = run_evaluation(
                dataset_path=args.dataset,
                model=args.model,
                judge_model=args.judge_model,
                pass_threshold=args.pass_threshold,
                score_threshold=args.score_threshold,
                verbose=args.verbose,
                dry_run=True,
            )
            print(f"✅ Dataset valid: {result.metrics.total_cases} cases")
            print("   Run without --dry-run to execute evaluation.")
            return 0

        # Run full evaluation
        print("🚀 Running evaluation...")
        if args.verbose:
            print()

        result = run_evaluation(
            dataset_path=args.dataset,
            model=args.model,
            judge_model=args.judge_model,
            pass_threshold=args.pass_threshold,
            score_threshold=args.score_threshold,
            max_workers=args.workers,
            verbose=args.verbose,
            dry_run=False,
        )

        # Print summary
        summary = format_summary(result, settings)
        print(summary)

        # Return appropriate exit code
        if result.metrics.overall_passed:
            return 0
        else:
            return 1

    except DatasetError as e:
        print(f"❌ Dataset error: {e}", file=sys.stderr)
        return 2

    except Exception as e:
        print(f"❌ Evaluation error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
