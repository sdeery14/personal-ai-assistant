"""CLI entry point for the eval pipeline.

Usage:
    python -m eval.pipeline <command> [OPTIONS]

Commands:
    trend       View eval pass rate trends over time
    check       Detect regressions against previous baseline
    run-evals   Run eval suite (core subset or full)
"""

import sys

from eval.pipeline.cli import pipeline


def main() -> None:
    """Entry point for ``python -m eval.pipeline``."""
    # Fix Windows console encoding for Unicode output
    import io

    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

    pipeline()


if __name__ == "__main__":
    main()
