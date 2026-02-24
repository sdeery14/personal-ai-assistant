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


def create_schedule_quality_judge(judge_model: str) -> object:
    """Create an LLM judge for evaluating schedule creation responses.

    Tailored for scheduling evals where the primary value is that the
    schedule was created correctly. Emphasizes confirmation over verbosity.

    Args:
        judge_model: Model identifier.

    Returns:
        MLflow judge scorer.
    """
    return make_judge(
        name="schedule_quality",
        instructions=(
            "You are evaluating whether an AI butler-style assistant "
            "appropriately handled a scheduling or reminder request.\n\n"
            "User request: {{ inputs }}\n"
            "Assistant response: {{ outputs }}\n"
            "Evaluation rubric: {{ expectations }}\n\n"
            "Evaluate ALL of the following criteria:\n"
            "1. ACTION TAKEN: The assistant actually created the schedule or "
            "reminder (confirmed it, not just discussed it)\n"
            "2. CONFIRMATION: Response confirms the schedule details (time, "
            "frequency, action) so the user knows it's set up\n"
            "3. CONCISE: Brief, professional confirmation — not overly verbose "
            "or padded with unnecessary caveats\n"
            "4. NATURAL: Reads like a competent assistant confirming an action, "
            "not a robotic system message\n\n"
            "IMPORTANT: A short, clear confirmation like 'Done — I'll check the "
            "weather every morning at 8am' is EXCELLENT. Brevity is a virtue "
            "for schedule confirmations.\n\n"
            "Rating guide:\n"
            "- excellent: Schedule created and confirmed clearly and concisely\n"
            "- good: Schedule created, confirmation has minor gaps\n"
            "- adequate: Schedule likely created but confirmation unclear\n"
            "- poor: No schedule created, or response is confusing/irrelevant\n\n"
            "Answer with ONLY one word: excellent, good, adequate, or poor."
        ),
        feedback_value_type=Literal["excellent", "good", "adequate", "poor"],
        model=f"openai:/{judge_model}",
    )


def create_notification_quality_judge(judge_model: str) -> object:
    """Create an LLM judge for evaluating notification judgment responses.

    Handles both cases: when a notification should be created (confirmation quality)
    and when no notification should be created (response quality).

    Args:
        judge_model: Model identifier.

    Returns:
        MLflow judge scorer.
    """
    return make_judge(
        name="notification_quality",
        instructions=(
            "You are evaluating an AI butler-style assistant's response to a "
            "user query that may or may not require creating a notification "
            "or reminder.\n\n"
            "User query: {{ inputs }}\n"
            "Assistant response: {{ outputs }}\n"
            "Evaluation rubric: {{ expectations }}\n\n"
            "Evaluate the response on these criteria:\n"
            "1. APPROPRIATE ACTION: If a reminder/notification was warranted, "
            "the assistant confirmed it was set up. If none was needed, the "
            "assistant responded directly without unnecessary notifications.\n"
            "2. HELPFUL: The response addresses the user's actual need\n"
            "3. NATURAL: Reads like a competent, warm assistant — not robotic\n"
            "4. CONCISE: Brief and to-the-point, no excessive caveats or padding\n\n"
            "IMPORTANT: A short, direct response is perfectly fine. Greetings, "
            "factual answers, and brief confirmations should all be rated "
            "highly if they address the user's need naturally.\n\n"
            "Rating guide:\n"
            "- excellent: Addresses the need perfectly with appropriate tone\n"
            "- good: Addresses the need with minor issues in tone or phrasing\n"
            "- adequate: Addresses the need but feels awkward or overly verbose\n"
            "- poor: Misses the point, creates confusion, or wrong action taken\n\n"
            "Answer with ONLY one word: excellent, good, adequate, or poor."
        ),
        feedback_value_type=Literal["excellent", "good", "adequate", "poor"],
        model=f"openai:/{judge_model}",
    )


def create_error_recovery_judge(judge_model: str) -> object:
    """Create an LLM judge for evaluating error recovery behavior.

    Scores responses on: graceful messaging, honesty, helpfulness, composure.

    Args:
        judge_model: Model identifier.

    Returns:
        MLflow judge scorer.
    """
    return make_judge(
        name="error_recovery_quality",
        instructions=(
            "You are evaluating how an AI butler-style assistant named Alfred "
            "handles situations where tools fail, data is missing, or requests "
            "are impossible to fulfill.\n\n"
            "User query: {{ inputs }}\n"
            "Assistant response: {{ outputs }}\n"
            "Error scenario: {{ expectations }}\n\n"
            "Evaluate ALL of the following criteria:\n"
            "1. GRACEFUL: No raw error messages, stack traces, or confusing "
            "technical jargon leaked to the user\n"
            "2. HONEST: Acknowledges limitations without hallucinating results "
            "or making up data it doesn't have\n"
            "3. HELPFUL: Offers alternatives, asks for clarification, or "
            "suggests next steps when possible\n"
            "4. COMPOSED: Maintains butler tone even when things go wrong — "
            "no panic, no excessive apologies\n\n"
            "Rating guide:\n"
            "- excellent: All 4 criteria strongly met\n"
            "- good: 3+ criteria met, minor gaps\n"
            "- adequate: 2 criteria met\n"
            "- poor: Raw errors shown, hallucinated data, or lost composure\n\n"
            "Answer with ONLY one word: excellent, good, adequate, or poor."
        ),
        feedback_value_type=Literal["excellent", "good", "adequate", "poor"],
        model=f"openai:/{judge_model}",
    )


def create_knowledge_connections_judge(judge_model: str) -> object:
    """Create an LLM judge for evaluating knowledge graph connection responses.

    Scores responses on: entity reference accuracy, relationship traversal,
    no hallucination, synthesis quality.

    Args:
        judge_model: Model identifier.

    Returns:
        MLflow judge scorer.
    """
    return make_judge(
        name="knowledge_connections_quality",
        instructions=(
            "You are evaluating whether an AI butler-style assistant named "
            "Alfred correctly uses knowledge graph data (entities and their "
            "relationships) to answer questions.\n\n"
            "User query: {{ inputs }}\n"
            "Assistant response: {{ outputs }}\n"
            "Evaluation rubric: {{ expectations }}\n\n"
            "Evaluate ALL of the following criteria:\n"
            "1. ENTITY ACCURACY: References entities that are relevant to "
            "the question from stored knowledge\n"
            "2. RELATIONSHIP AWARENESS: Demonstrates understanding of how "
            "entities are connected (works_on, depends_on, uses, etc.)\n"
            "3. NO HALLUCINATION: Does not invent entities or relationships "
            "that weren't in the knowledge graph\n"
            "4. SYNTHESIS: Combines knowledge from multiple entities/relationships "
            "into a coherent, useful answer\n\n"
            "Rating guide:\n"
            "- excellent: All 4 criteria strongly met, synthesizes connections well\n"
            "- good: 3+ criteria met, minor gaps in synthesis\n"
            "- adequate: 2 criteria met, some relevant entities referenced\n"
            "- poor: Ignored knowledge graph, hallucinated, or irrelevant answer\n\n"
            "Answer with ONLY one word: excellent, good, adequate, or poor."
        ),
        feedback_value_type=Literal["excellent", "good", "adequate", "poor"],
        model=f"openai:/{judge_model}",
    )


def create_contradiction_judge(judge_model: str) -> object:
    """Create a session-level LLM judge for contradiction handling conversations.

    Uses {{ conversation }} template variable for multi-turn evaluation.
    Evaluates whether the agent notices and handles conflicting information.

    Args:
        judge_model: Model identifier.

    Returns:
        MLflow judge scorer.
    """
    return make_judge(
        name="contradiction_quality",
        instructions=(
            "You are evaluating a multi-turn conversation between a user and "
            "an AI butler-style assistant named Alfred. The assistant has stored "
            "memories about the user, and the user provides information that "
            "contradicts or updates those stored facts.\n\n"
            "Conversation:\n{{ conversation }}\n\n"
            "Evaluate ALL of the following criteria:\n"
            "1. DETECTION: The assistant notices when new information conflicts "
            "with what it previously knew (from memory)\n"
            "2. GRACEFUL HANDLING: Addresses contradictions diplomatically — "
            "not accusatory ('You said X before, but now...') but clarifying "
            "('I have a note that X — would you like me to update that?')\n"
            "3. MEMORY UPDATE: Suggests or attempts to update stored information "
            "when the user confirms a change\n"
            "4. COHERENCE: Uses the corrected information consistently in "
            "subsequent turns, not the outdated data\n"
            "5. BUTLER TONE: Maintains composure and professionalism throughout\n\n"
            "Rating guide:\n"
            "- excellent: All 5 criteria strongly met\n"
            "- good: 4+ criteria met, minor gaps\n"
            "- adequate: 2-3 criteria met\n"
            "- poor: Missed contradictions, used outdated info, or was accusatory\n\n"
            "Answer with ONLY one word: excellent, good, adequate, or poor."
        ),
        feedback_value_type=Literal["excellent", "good", "adequate", "poor"],
        model=f"openai:/{judge_model}",
    )


def create_long_conversation_judge(judge_model: str) -> object:
    """Create a session-level LLM judge for long conversation coherence.

    Uses {{ conversation }} template variable for multi-turn evaluation.
    Evaluates context retention, consistency, and coherence over many turns.

    Args:
        judge_model: Model identifier.

    Returns:
        MLflow judge scorer.
    """
    return make_judge(
        name="long_conversation_quality",
        instructions=(
            "You are evaluating a long multi-turn conversation (8-10+ turns) "
            "between a user and an AI butler-style assistant named Alfred. "
            "The conversation shifts topics, circles back to earlier points, "
            "and tests whether the assistant maintains coherence.\n\n"
            "Conversation:\n{{ conversation }}\n\n"
            "Evaluate ALL of the following criteria:\n"
            "1. CONTEXT RETENTION: Accurately references information from "
            "earlier turns when relevant (doesn't forget what was discussed)\n"
            "2. NO SELF-CONTRADICTION: Never contradicts its own earlier "
            "statements within the conversation\n"
            "3. TOPIC TRANSITIONS: Handles topic shifts smoothly and can "
            "return to earlier threads naturally\n"
            "4. BUTLER TONE: Maintains consistent personality and tone "
            "throughout the entire conversation\n"
            "5. SUMMARY ACCURACY: If asked to summarize or reference earlier "
            "discussion, does so accurately\n\n"
            "Rating guide:\n"
            "- excellent: All 5 criteria strongly met across all turns\n"
            "- good: 4+ criteria met, minor lapses in later turns\n"
            "- adequate: 2-3 criteria met, some context loss\n"
            "- poor: Significant context loss, contradictions, or incoherence\n\n"
            "Answer with ONLY one word: excellent, good, adequate, or poor."
        ),
        feedback_value_type=Literal["excellent", "good", "adequate", "poor"],
        model=f"openai:/{judge_model}",
    )


def compute_notification_judgment(
    actual_notifications: list[dict],
    expected_notification: bool,
    actual_scheduled_tasks_count: int = 0,
) -> bool:
    """Check if proactive action matches expectation.

    Counts either notifications or scheduled tasks as proactive action.
    When a user asks "remind me at 3pm", creating a scheduled task is
    just as valid as creating a notification.

    Args:
        actual_notifications: Notifications found in DB after agent call.
        expected_notification: Whether a proactive action was expected.
        actual_scheduled_tasks_count: Number of scheduled tasks created.

    Returns:
        True if behavior matches expectation.
    """
    proactive_action_taken = len(actual_notifications) > 0 or actual_scheduled_tasks_count > 0
    if expected_notification:
        return proactive_action_taken
    else:
        return not proactive_action_taken


def compute_cron_equivalence(
    actual_cron: str,
    expected_cron: str,
    check_count: int = 5,
) -> bool:
    """Check if two cron expressions produce the same next N occurrences.

    Uses croniter to generate the next check_count occurrences from a fixed
    reference point and compares them.

    Args:
        actual_cron: Cron expression from the agent's scheduled task.
        expected_cron: Expected cron expression from the dataset.
        check_count: Number of future occurrences to compare.

    Returns:
        True if all next N occurrences match.
    """
    try:
        from croniter import croniter
        from datetime import datetime

        ref = datetime(2026, 3, 1, 0, 0)
        actual_iter = croniter(actual_cron, ref)
        expected_iter = croniter(expected_cron, ref)
        for _ in range(check_count):
            if actual_iter.get_next(datetime) != expected_iter.get_next(datetime):
                return False
        return True
    except Exception:
        return False


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
