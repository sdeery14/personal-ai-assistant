"""
Shared judge functions for the Alfred evaluation suite.

Provides reusable LLM judge creation for:
- Butler personality evaluation (tone, warmth, competence)
- Routing accuracy scoring (set match on tool calls)
"""

from typing import Literal

from mlflow.genai.judges import make_judge


def create_tone_judge(judge_model: str) -> object:
    """Create an LLM judge for evaluating butler personality and tone.

    Scores responses on: composed, competent, warm, no filler, adapts to context.
    Used by B1 (Tone) and as a component in other evals.

    Args:
        judge_model: Model identifier (e.g., 'gpt-4.1').

    Returns:
        MLflow judge scorer.
    """
    return make_judge(
        name="tone_quality",
        instructions=(
            "You are evaluating an AI butler-style assistant named Alfred. "
            "Alfred should be composed, competent, and genuinely warm — like "
            "a trusted household butler who anticipates needs.\n\n"
            "User message: {{ inputs }}\n"
            "Assistant response: {{ outputs }}\n"
            "Evaluation rubric: {{ expectations }}\n\n"
            "Evaluate ALL of the following criteria:\n"
            "1. TONE: Composed and professional, not overly casual or stiff\n"
            "2. NO FILLER: No 'I'd be happy to help!', no sycophantic openers, "
            "no 'Great question!' — gets straight to substance\n"
            "3. WARMTH: Genuine caring without being performative\n"
            "4. COMPETENCE: Response is substantive and directly useful\n"
            "5. ADAPTS: Matches the emotional register of the user's message "
            "(serious for crisis, celebratory for wins, efficient for busy)\n\n"
            "Rating guide:\n"
            "- excellent: All 5 criteria strongly met\n"
            "- good: 4+ criteria met, minor gaps\n"
            "- adequate: 2-3 criteria met\n"
            "- poor: Fewer than 2 criteria met, or uses filler phrases\n\n"
            "Answer with ONLY one word: excellent, good, adequate, or poor."
        ),
        feedback_value_type=Literal["excellent", "good", "adequate", "poor"],
        model=f"openai:/{judge_model}",
    )


def create_greeting_judge(judge_model: str) -> object:
    """Create an LLM judge for evaluating returning user greetings.

    Scores greetings on: personalization, proactiveness, citing basis, butler tone.

    Args:
        judge_model: Model identifier.

    Returns:
        MLflow judge scorer.
    """
    return make_judge(
        name="greeting_quality",
        instructions=(
            "You are evaluating a proactive greeting from an AI butler-style "
            "assistant named Alfred to a returning user.\n\n"
            "Greeting: {{ outputs }}\n"
            "Evaluation rubric: {{ expectations }}\n\n"
            "Evaluate ALL of the following criteria:\n"
            "1. PERSONALIZATION: References specific details from the user's "
            "known context (name, projects, preferences, schedule)\n"
            "2. PROACTIVENESS: Offers actionable help based on what it knows "
            "(e.g., upcoming deadlines, pending tasks, recent events)\n"
            "3. BUTLER TONE: Composed, warm, professional — not a generic "
            "'Welcome back!' or chatbot-style greeting\n"
            "4. NO HALLUCINATION: Only references things that could plausibly "
            "come from stored memories, never invents details\n\n"
            "Rating guide:\n"
            "- excellent: All 4 criteria strongly met, greeting feels personal\n"
            "- good: 3+ criteria met, minor gaps in specificity\n"
            "- adequate: 2 criteria met, somewhat generic\n"
            "- poor: Generic greeting, no personalization, or hallucinated details\n\n"
            "Answer with ONLY one word: excellent, good, adequate, or poor."
        ),
        feedback_value_type=Literal["excellent", "good", "adequate", "poor"],
        model=f"openai:/{judge_model}",
    )


def create_memory_informed_judge(judge_model: str) -> object:
    """Create a session-level LLM judge for memory-informed conversations.

    Uses {{ conversation }} template variable for multi-turn evaluation.
    Evaluates whether the agent applies stored memories naturally.

    Args:
        judge_model: Model identifier.

    Returns:
        MLflow judge scorer.
    """
    return make_judge(
        name="memory_informed_quality",
        instructions=(
            "You are evaluating a multi-turn conversation between a user and "
            "an AI butler-style assistant named Alfred. The assistant has access "
            "to stored memories about the user.\n\n"
            "Conversation:\n{{ conversation }}\n\n"
            "Evaluate ALL of the following criteria:\n"
            "1. MEMORY APPLICATION: The assistant uses stored knowledge "
            "to give personalized, context-aware responses\n"
            "2. NATURAL CITATION: Information from memory is woven into "
            "responses naturally, not awkwardly listed\n"
            "3. HELPFUL: Responses are substantive and directly useful for "
            "the user's actual need\n"
            "4. BUTLER TONE: Composed, warm, professional throughout\n"
            "5. COHERENCE: Conversation flows naturally across turns\n\n"
            "Rating guide:\n"
            "- excellent: All 5 criteria strongly met\n"
            "- good: 4+ criteria met, minor gaps\n"
            "- adequate: 2-3 criteria met\n"
            "- poor: Memory not applied, or responses generic/unhelpful\n\n"
            "Answer with ONLY one word: excellent, good, adequate, or poor."
        ),
        feedback_value_type=Literal["excellent", "good", "adequate", "poor"],
        model=f"openai:/{judge_model}",
    )


def create_multi_cap_judge(judge_model: str) -> object:
    """Create a session-level LLM judge for multi-capability conversations.

    Evaluates synthesis quality, goal completion, and multi-tool usage.

    Args:
        judge_model: Model identifier.

    Returns:
        MLflow judge scorer.
    """
    return make_judge(
        name="multi_cap_quality",
        instructions=(
            "You are evaluating a multi-turn conversation between a user and "
            "an AI butler-style assistant named Alfred. The conversation involves "
            "a realistic goal requiring multiple capabilities (memory recall, "
            "weather, knowledge graph, scheduling, etc.).\n\n"
            "Conversation:\n{{ conversation }}\n\n"
            "Evaluate ALL of the following criteria:\n"
            "1. SYNTHESIS: The assistant combines information from multiple "
            "sources (memory, weather, knowledge) into coherent responses\n"
            "2. GOAL COMPLETION: The user's objective is meaningfully advanced "
            "or completed across the conversation\n"
            "3. TOOL USAGE: The assistant leverages its capabilities appropriately "
            "(not over-using or under-using tools)\n"
            "4. BUTLER TONE: Composed, warm, professional throughout\n"
            "5. COHERENCE: Multi-turn conversation flows naturally\n\n"
            "Rating guide:\n"
            "- excellent: All 5 criteria strongly met\n"
            "- good: 4+ criteria met, minor gaps\n"
            "- adequate: 2-3 criteria met\n"
            "- poor: Failed to synthesize, or conversation disjointed\n\n"
            "Answer with ONLY one word: excellent, good, adequate, or poor."
        ),
        feedback_value_type=Literal["excellent", "good", "adequate", "poor"],
        model=f"openai:/{judge_model}",
    )


def create_routing_quality_judge(judge_model: str) -> object:
    """Create an LLM judge for evaluating routing response quality.

    Lighter-weight than the tone judge — focuses on helpfulness and relevance
    rather than full butler personality in every response.

    Args:
        judge_model: Model identifier.

    Returns:
        MLflow judge scorer.
    """
    return make_judge(
        name="routing_quality",
        instructions=(
            "You are evaluating whether an AI assistant's response is helpful "
            "and appropriate for the user's query.\n\n"
            "User query: {{ inputs }}\n"
            "Assistant response: {{ outputs }}\n"
            "Evaluation rubric: {{ expectations }}\n\n"
            "Evaluate ALL of the following criteria:\n"
            "1. RELEVANCE: Response directly addresses the user's query\n"
            "2. HELPFULNESS: Response provides useful, actionable information\n"
            "3. NATURALNESS: Response reads naturally, not robotic or overly verbose\n"
            "4. APPROPRIATENESS: Response matches the tone and depth the query warrants\n\n"
            "Rating guide:\n"
            "- excellent: All 4 criteria strongly met\n"
            "- good: 3+ criteria met, minor gaps\n"
            "- adequate: 2 criteria met\n"
            "- poor: Response is irrelevant, unhelpful, or badly structured\n\n"
            "Answer with ONLY one word: excellent, good, adequate, or poor."
        ),
        feedback_value_type=Literal["excellent", "good", "adequate", "poor"],
        model=f"openai:/{judge_model}",
    )


def compute_routing_accuracy(
    actual_delegations: list[str],
    expected_delegations: list[str],
) -> bool:
    """Check if actual tool delegations match expected delegations.

    Uses set matching: all expected delegations must appear in actuals.
    Extra delegations are acceptable (agent may use additional tools).

    Args:
        actual_delegations: Tool names actually called by the agent.
        expected_delegations: Tool names expected to be called.

    Returns:
        True if all expected delegations are present in actuals.
    """
    if not expected_delegations:
        # No delegation expected — should NOT have any ask_*_agent calls
        agent_calls = [d for d in actual_delegations if d.startswith("ask_")]
        return len(agent_calls) == 0

    expected_set = set(expected_delegations)
    actual_set = set(actual_delegations)
    return expected_set.issubset(actual_set)
