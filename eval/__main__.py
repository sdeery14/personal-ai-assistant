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
from eval.runner import (
    ContradictionHandlingEvaluationResult,
    ErrorRecoveryEvaluationResult,
    EvaluationResult,
    GraphExtractionEvaluationResult,
    KnowledgeConnectionsEvaluationResult,
    LongConversationEvaluationResult,
    MemoryEvaluationResult,
    MemoryInformedEvaluationResult,
    MemoryWriteEvaluationResult,
    MultiCapEvaluationResult,
    NotificationJudgmentEvaluationResult,
    OnboardingEvaluationResult,
    ReturningGreetingEvaluationResult,
    RoutingEvaluationResult,
    ScheduleCronEvaluationResult,
    ToneEvaluationResult,
    WeatherEvaluationResult,
    format_contradiction_handling_summary,
    format_error_recovery_summary,
    format_graph_extraction_summary,
    format_knowledge_connections_summary,
    format_long_conversation_summary,
    format_memory_informed_summary,
    format_memory_summary,
    format_memory_write_summary,
    format_multi_cap_summary,
    format_notification_judgment_summary,
    format_onboarding_summary,
    format_returning_greeting_summary,
    format_routing_summary,
    format_schedule_cron_summary,
    format_summary,
    format_tone_summary,
    format_weather_summary,
    is_contradiction_handling_dataset,
    is_error_recovery_dataset,
    is_graph_extraction_dataset,
    is_knowledge_connections_dataset,
    is_long_conversation_dataset,
    is_memory_dataset,
    is_memory_informed_dataset,
    is_memory_write_dataset,
    is_multi_cap_dataset,
    is_notification_judgment_dataset,
    is_onboarding_dataset,
    is_returning_greeting_dataset,
    is_routing_dataset,
    is_schedule_cron_dataset,
    is_tone_dataset,
    is_weather_dataset,
    run_contradiction_handling_evaluation,
    run_error_recovery_evaluation,
    run_evaluation,
    run_graph_evaluation,
    run_knowledge_connections_evaluation,
    run_long_conversation_evaluation,
    run_memory_evaluation,
    run_memory_informed_evaluation,
    run_memory_write_evaluation,
    run_multi_cap_evaluation,
    run_notification_judgment_evaluation,
    run_onboarding_evaluation,
    run_returning_greeting_evaluation,
    run_routing_evaluation,
    run_schedule_cron_evaluation,
    run_tone_evaluation,
    run_weather_evaluation,
)


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
        "--prompt-alias",
        type=str,
        default=None,
        help="Prompt registry alias to load prompts from (default: PROMPT_ALIAS env var or 'production')",
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

    # Apply --prompt-alias to environment before loading settings
    if args.prompt_alias:
        import os
        os.environ["PROMPT_ALIAS"] = args.prompt_alias

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
        # Check dataset type (order matters — more specific checks first)
        # Alfred evals use eval_type field for definitive detection, so check them
        # before onboarding which uses heuristic field matching (user_turns + persona).
        is_graph_ext = is_graph_extraction_dataset(args.dataset)
        is_memory_write = is_memory_write_dataset(args.dataset)
        is_ret_greeting = is_returning_greeting_dataset(args.dataset)
        is_mem_informed = is_memory_informed_dataset(args.dataset)
        is_tone = is_tone_dataset(args.dataset)
        is_routing = is_routing_dataset(args.dataset)
        is_mcap = is_multi_cap_dataset(args.dataset)
        # Tier 2 Alfred evals
        is_notif = is_notification_judgment_dataset(args.dataset)
        is_errrecov = is_error_recovery_dataset(args.dataset)
        is_cron = is_schedule_cron_dataset(args.dataset)
        is_kg = is_knowledge_connections_dataset(args.dataset)
        is_contra = is_contradiction_handling_dataset(args.dataset)
        is_longconv = is_long_conversation_dataset(args.dataset)
        is_onboarding = is_onboarding_dataset(args.dataset) and not is_ret_greeting and not is_mem_informed and not is_mcap and not is_contra and not is_longconv
        is_memory = is_memory_dataset(args.dataset) and not is_memory_write and not is_mem_informed
        is_weather = is_weather_dataset(args.dataset)

        if is_graph_ext:
            # Graph extraction evaluation flow
            if args.dry_run:
                print("Validating graph extraction dataset (dry run)...")
                result = run_graph_evaluation(
                    dataset_path=args.dataset,
                    verbose=args.verbose,
                    dry_run=True,
                )
                print(f"Graph extraction dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0

            print("Running graph extraction evaluation...")
            if args.verbose:
                print()

            result = run_graph_evaluation(
                dataset_path=args.dataset,
                verbose=args.verbose,
                dry_run=False,
            )

            summary = format_graph_extraction_summary(result)
            print(summary)

            if result.metrics.overall_passed:
                return 0
            else:
                return 1

        elif is_memory_write:
            # Memory write evaluation flow
            if args.dry_run:
                print("Validating memory write dataset (dry run)...")
                result = run_memory_write_evaluation(
                    dataset_path=args.dataset,
                    verbose=args.verbose,
                    dry_run=True,
                )
                print(f"Memory write dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0

            print("Running memory write evaluation...")
            if args.verbose:
                print()

            result = run_memory_write_evaluation(
                dataset_path=args.dataset,
                verbose=args.verbose,
                dry_run=False,
            )

            summary = format_memory_write_summary(result)
            print(summary)

            if result.metrics.overall_passed:
                return 0
            else:
                return 1

        elif is_onboarding:
            # Onboarding evaluation flow
            if args.dry_run:
                print("Validating onboarding dataset (dry run)...")
                result = run_onboarding_evaluation(
                    dataset_path=args.dataset,
                    verbose=args.verbose,
                    dry_run=True,
                )
                print(f"Onboarding dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0

            print("Running onboarding evaluation...")
            if args.verbose:
                print()

            result = run_onboarding_evaluation(
                dataset_path=args.dataset,
                verbose=args.verbose,
                dry_run=False,
            )

            summary = format_onboarding_summary(result)
            print(summary)

            if result.metrics.overall_passed:
                return 0
            else:
                return 1

        elif is_ret_greeting:
            if args.dry_run:
                print("Validating returning greeting dataset (dry run)...")
                result = run_returning_greeting_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=True)
                print(f"Returning greeting dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0
            print("Running returning greeting evaluation...")
            if args.verbose:
                print()
            result = run_returning_greeting_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=False)
            print(format_returning_greeting_summary(result))
            return 0 if result.metrics.overall_passed else 1

        elif is_mem_informed:
            if args.dry_run:
                print("Validating memory-informed dataset (dry run)...")
                result = run_memory_informed_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=True)
                print(f"Memory-informed dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0
            print("Running memory-informed evaluation...")
            if args.verbose:
                print()
            result = run_memory_informed_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=False)
            print(format_memory_informed_summary(result))
            return 0 if result.metrics.overall_passed else 1

        elif is_tone:
            if args.dry_run:
                print("Validating tone dataset (dry run)...")
                result = run_tone_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=True)
                print(f"Tone dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0
            print("Running tone & personality evaluation...")
            if args.verbose:
                print()
            result = run_tone_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=False)
            print(format_tone_summary(result))
            return 0 if result.metrics.overall_passed else 1

        elif is_routing:
            if args.dry_run:
                print("Validating routing dataset (dry run)...")
                result = run_routing_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=True)
                print(f"Routing dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0
            print("Running orchestrator routing evaluation...")
            if args.verbose:
                print()
            result = run_routing_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=False)
            print(format_routing_summary(result))
            return 0 if result.metrics.overall_passed else 1

        elif is_mcap:
            if args.dry_run:
                print("Validating multi-capability dataset (dry run)...")
                result = run_multi_cap_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=True)
                print(f"Multi-capability dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0
            print("Running multi-capability evaluation...")
            if args.verbose:
                print()
            result = run_multi_cap_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=False)
            print(format_multi_cap_summary(result))
            return 0 if result.metrics.overall_passed else 1

        elif is_notif:
            if args.dry_run:
                print("Validating notification judgment dataset (dry run)...")
                result = run_notification_judgment_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=True)
                print(f"Notification judgment dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0
            print("Running notification judgment evaluation...")
            if args.verbose:
                print()
            result = run_notification_judgment_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=False)
            print(format_notification_judgment_summary(result))
            return 0 if result.metrics.overall_passed else 1

        elif is_errrecov:
            if args.dry_run:
                print("Validating error recovery dataset (dry run)...")
                result = run_error_recovery_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=True)
                print(f"Error recovery dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0
            print("Running error recovery evaluation...")
            if args.verbose:
                print()
            result = run_error_recovery_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=False)
            print(format_error_recovery_summary(result))
            return 0 if result.metrics.overall_passed else 1

        elif is_cron:
            if args.dry_run:
                print("Validating schedule cron dataset (dry run)...")
                result = run_schedule_cron_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=True)
                print(f"Schedule cron dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0
            print("Running schedule cron accuracy evaluation...")
            if args.verbose:
                print()
            result = run_schedule_cron_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=False)
            print(format_schedule_cron_summary(result))
            return 0 if result.metrics.overall_passed else 1

        elif is_kg:
            if args.dry_run:
                print("Validating knowledge connections dataset (dry run)...")
                result = run_knowledge_connections_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=True)
                print(f"Knowledge connections dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0
            print("Running knowledge graph connections evaluation...")
            if args.verbose:
                print()
            result = run_knowledge_connections_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=False)
            print(format_knowledge_connections_summary(result))
            return 0 if result.metrics.overall_passed else 1

        elif is_contra:
            if args.dry_run:
                print("Validating contradiction handling dataset (dry run)...")
                result = run_contradiction_handling_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=True)
                print(f"Contradiction handling dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0
            print("Running contradiction handling evaluation...")
            if args.verbose:
                print()
            result = run_contradiction_handling_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=False)
            print(format_contradiction_handling_summary(result))
            return 0 if result.metrics.overall_passed else 1

        elif is_longconv:
            if args.dry_run:
                print("Validating long conversation dataset (dry run)...")
                result = run_long_conversation_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=True)
                print(f"Long conversation dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0
            print("Running long conversation coherence evaluation...")
            if args.verbose:
                print()
            result = run_long_conversation_evaluation(dataset_path=args.dataset, verbose=args.verbose, dry_run=False)
            print(format_long_conversation_summary(result))
            return 0 if result.metrics.overall_passed else 1

        elif is_weather:
            # Weather evaluation flow
            if args.dry_run:
                print("🔍 Validating weather dataset (dry run)...")
                result = run_weather_evaluation(
                    dataset_path=args.dataset,
                    verbose=args.verbose,
                    dry_run=True,
                )
                print(f"✅ Weather dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0

            print("🚀 Running weather evaluation...")
            if args.verbose:
                print()

            result = run_weather_evaluation(
                dataset_path=args.dataset,
                verbose=args.verbose,
                dry_run=False,
            )

            # Print summary
            summary = format_weather_summary(result)
            print(summary)

            # Return exit code based on weather gate
            if result.metrics.overall_passed:
                return 0
            else:
                return 1

        elif is_memory:
            # Memory evaluation flow
            if args.dry_run:
                print("🔍 Validating memory dataset (dry run)...")
                result = run_memory_evaluation(
                    dataset_path=args.dataset,
                    verbose=args.verbose,
                    dry_run=True,
                )
                print(f"✅ Memory dataset valid: {result.metrics.total_cases} cases")
                print("   Run without --dry-run to execute evaluation.")
                return 0

            print("🚀 Running memory evaluation...")
            if args.verbose:
                print()

            result = run_memory_evaluation(
                dataset_path=args.dataset,
                verbose=args.verbose,
                dry_run=False,
            )

            # Print summary
            summary = format_memory_summary(result)
            print(summary)

            # Return exit code based on memory gate
            if result.metrics.overall_passed:
                return 0
            else:
                return 1

        else:
            # Standard evaluation flow
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
            # For security datasets, check security_gate_passed; otherwise check overall_passed
            if result.metrics.security_gate_passed is not None:
                # Security dataset: use security gate
                if result.metrics.security_gate_passed:
                    return 0
                else:
                    return 1
            else:
                # Quality dataset: use overall_passed
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
