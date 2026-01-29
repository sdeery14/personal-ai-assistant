"""
LLM judge definition for evaluation.

This module creates the quality judge using mlflow.genai.judges.make_judge.
The judge evaluates assistant responses against rubrics and returns scores
on a 1-5 scale.
"""

from typing import Literal

from mlflow.genai.judges import make_judge

from eval.config import get_eval_settings


def create_quality_judge():
    """
    Create the quality evaluation judge.

    The judge evaluates assistant responses based on:
    - The user's original question (from inputs)
    - The assistant's response (from outputs)
    - The evaluation rubric (from expectations)

    Returns:
        A judge object compatible with mlflow.genai.evaluate()

    Scoring Scale:
        5 (Excellent): Fully addresses the question, accurate, well-structured
        4 (Good): Addresses the question correctly with minor issues
        3 (Acceptable): Partially addresses the question; some inaccuracies
        2 (Poor): Significantly misses the point, contains notable errors
        1 (Unacceptable): Completely wrong, irrelevant, or harmful

    Pass Threshold:
        Score >= 4 is considered PASS
        Score < 4 is considered FAIL
    """
    settings = get_eval_settings()

    # MLflow 3.x uses top-level template variables: inputs, outputs, expectations
    # These are passed as dicts to the judge
    quality_judge = make_judge(
        name="quality",
        instructions="""You are an evaluation judge for an AI assistant.

## Task
Evaluate the assistant's response quality based on the provided rubric.

## Input
**User Question**: {{ inputs }}
**Assistant Response**: {{ outputs }}
**Evaluation Rubric**: {{ expectations }}

## Scoring Scale
- **5 (Excellent)**: Fully addresses the question, accurate, well-structured, follows rubric perfectly
- **4 (Good)**: Addresses the question correctly with minor issues or room for improvement
- **3 (Acceptable)**: Partially addresses the question; some inaccuracies or missing elements
- **2 (Poor)**: Significantly misses the point, contains notable errors, or ignores rubric
- **1 (Unacceptable)**: Completely wrong, irrelevant, or harmful

## Instructions
1. Read the user question carefully
2. Review the assistant's response
3. Evaluate against the rubric criteria
4. Assign a score from 1-5
5. Provide a brief justification (1-2 sentences)

Return ONLY the numeric score (1, 2, 3, 4, or 5).""",
        feedback_value_type=Literal["1", "2", "3", "4", "5"],
        model=f"openai:/{settings.judge_model}",
    )

    return quality_judge


# Score interpretation constants
PASS_THRESHOLD = 4  # Score >= 4 is PASS
SCORE_LABELS = {
    1: "Unacceptable",
    2: "Poor",
    3: "Acceptable",
    4: "Good",
    5: "Excellent",
}


def score_to_passed(score: int) -> bool:
    """Convert a score to a pass/fail boolean."""
    return score >= PASS_THRESHOLD


def score_to_label(score: int) -> str:
    """Get human-readable label for a score."""
    return SCORE_LABELS.get(score, "Unknown")
