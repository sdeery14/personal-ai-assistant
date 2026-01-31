"""Unit tests for guardrails module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from agents import Agent, GuardrailFunctionOutput, RunContextWrapper

from src.services.guardrails import moderate_with_retry, validate_input, validate_output


def create_mock_moderation(flagged: bool, flagged_category: str | None = None):
    """Helper to create mock Moderation response.

    Args:
        flagged: Whether content should be flagged
        flagged_category: Category to flag (e.g., 'harassment', 'hate', 'violence')

    Returns:
        Mock object matching OpenAI Moderation API response structure
    """
    # All categories default to False
    categories = MagicMock()
    for cat in [
        "harassment",
        "harassment_threatening",
        "hate",
        "hate_threatening",
        "illicit",
        "illicit_violent",
        "self_harm",
        "self_harm_instructions",
        "self_harm_intent",
        "sexual",
        "sexual_minors",
        "violence",
        "violence_graphic",
    ]:
        setattr(categories, cat, False)

    # Set the flagged category to True if specified
    if flagged and flagged_category:
        setattr(categories, flagged_category, True)

    # Create mock result
    result = MagicMock()
    result.flagged = flagged
    result.categories = categories
    result.categories.model_dump.return_value = {
        cat: getattr(categories, cat)
        for cat in [
            "harassment",
            "harassment_threatening",
            "hate",
            "hate_threatening",
            "illicit",
            "illicit_violent",
            "self_harm",
            "self_harm_instructions",
            "self_harm_intent",
            "sexual",
            "sexual_minors",
            "violence",
            "violence_graphic",
        ]
    }

    # Create mock moderation response
    moderation = MagicMock()
    moderation.results = [result]

    return moderation


@pytest.fixture
def mock_correlation_id():
    """Fixture for test correlation ID."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def mock_agent():
    """Fixture for test agent."""
    return Agent(name="TestAgent", instructions="Test instructions", model="gpt-4")


@pytest.fixture
def mock_context(mock_correlation_id):
    """Fixture for mock RunContextWrapper with correlation_id."""
    context = RunContextWrapper(context={"correlation_id": mock_correlation_id})
    return context


class TestModerateWithRetry:
    """Tests for moderate_with_retry function."""

    @pytest.mark.asyncio
    async def test_moderate_with_retry_allows_safe_content(self, mock_correlation_id):
        """Test that safe content passes moderation."""
        mock_moderation = create_mock_moderation(flagged=False)

        with patch("src.services.guardrails.AsyncOpenAI") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.moderations.create.return_value = mock_moderation
            mock_client_class.return_value = mock_client

            is_flagged, category, retry_count = await moderate_with_retry(
                "What is 2+2?", mock_correlation_id
            )

            assert is_flagged is False
            assert category is None
            assert retry_count == 0
            mock_client.moderations.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_moderate_with_retry_blocks_unsafe_content(self, mock_correlation_id):
        """Test that unsafe content is flagged by moderation."""
        mock_moderation = create_mock_moderation(
            flagged=True, flagged_category="harassment"
        )

        with patch("src.services.guardrails.AsyncOpenAI") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.moderations.create.return_value = mock_moderation
            mock_client_class.return_value = mock_client

            is_flagged, category, retry_count = await moderate_with_retry(
                "unsafe content", mock_correlation_id
            )

            assert is_flagged is True
            assert category == "harassment"
            assert retry_count == 0

    @pytest.mark.asyncio
    async def test_moderate_with_retry_exponential_backoff(self, mock_correlation_id):
        """Test that retry logic uses exponential backoff delays."""
        with patch("src.services.guardrails.AsyncOpenAI") as mock_client_class:
            mock_client = AsyncMock()
            # Fail 3 times, then succeed on 4th attempt
            mock_client.moderations.create.side_effect = [
                Exception("API Error 1"),
                Exception("API Error 2"),
                Exception("API Error 3"),
                create_mock_moderation(flagged=False),
            ]
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                start_time = asyncio.get_event_loop().time()
                is_flagged, category, retry_count = await moderate_with_retry(
                    "test content", mock_correlation_id, max_retries=3
                )

                # Verify delays follow exponential backoff pattern
                # Delays are: 0 (no delay on first failure), 0.1, 0.5 for retries
                assert mock_sleep.call_count == 3
                # Check the delay values
                delay_calls = [call.args[0] for call in mock_sleep.call_args_list]
                assert delay_calls == [
                    0,
                    0.1,
                    0.5,
                ]  # First attempt has 0 delay internally before retries start

                assert is_flagged is False
                assert retry_count == 3

    @pytest.mark.asyncio
    async def test_moderate_with_retry_fail_closed(self, mock_correlation_id):
        """Test that after exhausting retries, function fails closed (blocks content)."""
        with patch("src.services.guardrails.AsyncOpenAI") as mock_client_class:
            mock_client = AsyncMock()
            # Fail all 4 attempts (initial + 3 retries)
            mock_client.moderations.create.side_effect = Exception(
                "Persistent API Error"
            )
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                is_flagged, category, retry_count = await moderate_with_retry(
                    "test content", mock_correlation_id, max_retries=3
                )

                # Should fail closed after exhausting retries
                assert is_flagged is True
                assert category == "moderation_api_failure"
                assert retry_count == 3


# NOTE: validate_input and validate_output are decorated with @sdk_input_guardrail
# and @sdk_output_guardrail, which wraps them as InputGuardrail/OutputGuardrail objects.
# These cannot be tested directly via unit tests as they require the Agent SDK runtime.
# Per testing philosophy: guardrail effectiveness is validated via MLflow eval (Phase 5)
# with real API calls against the security golden dataset.


class TestGuardrailExceptions:
    """Tests for guardrail exception attributes (T054)."""

    def test_input_guardrail_exception_exists(self):
        """T054: Verify InputGuardrailTripwireTriggered exception exists and can be imported."""
        from agents.exceptions import InputGuardrailTripwireTriggered

        # Verify exception class exists
        assert InputGuardrailTripwireTriggered is not None
        assert issubclass(InputGuardrailTripwireTriggered, Exception)

        # SDK exception requires InputGuardrailResult object, not string
        # We verify it exists for catching in our code

    def test_output_guardrail_exception_exists(self):
        """T054: Verify OutputGuardrailTripwireTriggered exception exists and can be imported."""
        from agents.exceptions import OutputGuardrailTripwireTriggered

        # Verify exception class exists
        assert OutputGuardrailTripwireTriggered is not None
        assert issubclass(OutputGuardrailTripwireTriggered, Exception)

    def test_guardrail_function_output_structure(self):
        """T054: Verify GuardrailFunctionOutput structure from SDK."""
        # Import from the correct location
        from agents import GuardrailFunctionOutput

        # Create output object with correct signature
        output = GuardrailFunctionOutput(
            output_info="Content flagged as unsafe", tripwire_triggered=True
        )

        # Verify attributes
        assert output.tripwire_triggered is True
        assert output.output_info == "Content flagged as unsafe"

        # Test non-triggered case
        safe_output = GuardrailFunctionOutput(
            output_info=None, tripwire_triggered=False
        )
        assert safe_output.tripwire_triggered is False
        assert safe_output.output_info is None
