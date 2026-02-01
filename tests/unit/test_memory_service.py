"""Unit tests for memory service."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.memory import MemoryItem, MemoryQueryRequest, MemoryType
from src.services.memory_service import MemoryService


@pytest.fixture
def memory_service():
    """Create memory service instance for testing."""
    with patch("src.services.memory_service.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            token_budget=1000,
            min_relevance=0.3,
            max_results=10,
            rrf_k=60,
            openai_api_key="test-key",
            embedding_model="text-embedding-3-small",
        )
        return MemoryService()


@pytest.fixture
def sample_memory_items():
    """Create sample memory items for testing."""
    now = datetime.now(timezone.utc)
    return [
        MemoryItem(
            id=uuid4(),
            user_id="test-user",
            content="User prefers uv over pip",
            type=MemoryType.PREFERENCE,
            relevance_score=0.9,
            created_at=now,
            importance=0.8,
        ),
        MemoryItem(
            id=uuid4(),
            user_id="test-user",
            content="Project uses FastAPI and Docker",
            type=MemoryType.FACT,
            relevance_score=0.7,
            created_at=now,
            importance=0.6,
        ),
        MemoryItem(
            id=uuid4(),
            user_id="test-user",
            content="Decided to use hybrid search for memory retrieval",
            type=MemoryType.DECISION,
            relevance_score=0.5,
            created_at=now,
            importance=0.9,
        ),
    ]


class TestTokenCounting:
    """Tests for token counting functionality."""

    def test_count_tokens_simple(self, memory_service):
        """Test token counting for simple text."""
        text = "Hello, world!"
        tokens = memory_service.count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_count_tokens_empty(self, memory_service):
        """Test token counting for empty string."""
        tokens = memory_service.count_tokens("")
        assert tokens == 0


class TestTokenBudget:
    """Tests for token budget enforcement."""

    def test_enforce_token_budget_under_budget(self, memory_service, sample_memory_items):
        """Test that items under budget are not truncated."""
        result, truncated = memory_service.enforce_token_budget(
            sample_memory_items, budget=10000
        )

        assert len(result) == len(sample_memory_items)
        assert truncated is False

    def test_enforce_token_budget_truncates(self, memory_service, sample_memory_items):
        """Test that items over budget are truncated."""
        # Use very small budget to force truncation
        result, truncated = memory_service.enforce_token_budget(
            sample_memory_items, budget=10
        )

        assert len(result) < len(sample_memory_items)
        assert truncated is True

    def test_enforce_token_budget_returns_truncated_flag(self, memory_service, sample_memory_items):
        """Test that truncated flag is correctly set."""
        # Under budget
        _, truncated1 = memory_service.enforce_token_budget(
            sample_memory_items, budget=10000
        )
        assert truncated1 is False

        # Over budget
        _, truncated2 = memory_service.enforce_token_budget(
            sample_memory_items, budget=5
        )
        assert truncated2 is True


class TestRRFFusion:
    """Tests for Reciprocal Rank Fusion."""

    def test_rrf_fusion_combines_rankings(self, memory_service, sample_memory_items):
        """Test that RRF correctly combines rankings from both sources."""
        # Create keyword and semantic results with overlapping items
        keyword_results = [
            (sample_memory_items[0], 1),  # Item 0 at rank 1
            (sample_memory_items[1], 2),  # Item 1 at rank 2
        ]
        semantic_results = [
            (sample_memory_items[1], 1),  # Item 1 at rank 1 (different from keyword)
            (sample_memory_items[0], 2),  # Item 0 at rank 2
            (sample_memory_items[2], 3),  # Item 2 only in semantic
        ]

        result = memory_service.rrf_fusion(keyword_results, semantic_results, k=60)

        assert len(result) == 3  # All unique items
        # Items appearing in both lists should have higher scores
        # Item 0 and 1 both appear in both lists

    def test_rrf_fusion_handles_disjoint_results(self, memory_service, sample_memory_items):
        """Test RRF with completely disjoint result sets."""
        keyword_results = [(sample_memory_items[0], 1)]
        semantic_results = [(sample_memory_items[1], 1)]

        result = memory_service.rrf_fusion(keyword_results, semantic_results, k=60)

        assert len(result) == 2
        # Both items should be present
        item_ids = {item.id for item in result}
        assert sample_memory_items[0].id in item_ids
        assert sample_memory_items[1].id in item_ids

    def test_rrf_fusion_empty_inputs(self, memory_service):
        """Test RRF with empty inputs."""
        result = memory_service.rrf_fusion([], [], k=60)
        assert result == []

    def test_rrf_fusion_one_empty(self, memory_service, sample_memory_items):
        """Test RRF when one input is empty."""
        keyword_results = [(sample_memory_items[0], 1)]
        semantic_results = []

        result = memory_service.rrf_fusion(keyword_results, semantic_results, k=60)

        assert len(result) == 1
        assert result[0].id == sample_memory_items[0].id


class TestHybridSearch:
    """Tests for hybrid search functionality."""

    @pytest.mark.asyncio
    async def test_hybrid_search_enforces_user_id_filter(self, memory_service):
        """Test that hybrid search always includes user_id filter (CRITICAL)."""
        request = MemoryQueryRequest(
            user_id="test-user",
            query="test query",
        )

        with patch.object(
            memory_service.embedding_service, "get_embedding", return_value=[0.1] * 1536
        ):
            with patch.object(
                memory_service, "keyword_search", return_value=[]
            ) as mock_keyword:
                with patch.object(
                    memory_service, "semantic_search", return_value=[]
                ) as mock_semantic:
                    await memory_service.hybrid_search(request)

                    # Verify user_id is passed to both search methods
                    mock_keyword.assert_called_once()
                    assert mock_keyword.call_args.kwargs["user_id"] == "test-user"

                    mock_semantic.assert_called_once()
                    assert mock_semantic.call_args.kwargs["user_id"] == "test-user"

    @pytest.mark.asyncio
    async def test_hybrid_search_filters_by_min_score(self, memory_service, sample_memory_items):
        """Test that results below min_score are filtered out."""
        # Create items with varying scores
        low_score_item = sample_memory_items[2]
        low_score_item.relevance_score = 0.1  # Below default 0.3 threshold

        request = MemoryQueryRequest(
            user_id="test-user",
            query="test query",
            min_score=0.3,
        )

        keyword_results = [(sample_memory_items[0], 1)]  # High score
        semantic_results = [(low_score_item, 1)]  # Low score

        with patch.object(
            memory_service.embedding_service, "get_embedding", return_value=[0.1] * 1536
        ):
            with patch.object(
                memory_service, "keyword_search", return_value=keyword_results
            ):
                with patch.object(
                    memory_service, "semantic_search", return_value=semantic_results
                ):
                    response = await memory_service.hybrid_search(request)

                    # Low score items should be filtered
                    for item in response.items:
                        assert item.relevance_score >= 0.3

    @pytest.mark.asyncio
    async def test_database_error_returns_empty_response(self, memory_service):
        """Test that database errors result in empty response (fail closed)."""
        request = MemoryQueryRequest(
            user_id="test-user",
            query="test query",
        )

        with patch.object(
            memory_service.embedding_service, "get_embedding", return_value=[0.1] * 1536
        ):
            with patch.object(
                memory_service, "keyword_search", side_effect=Exception("DB Error")
            ):
                response = await memory_service.hybrid_search(request)

                # Should return empty response, not raise exception
                assert response.items == []
                assert response.total_count == 0

    @pytest.mark.asyncio
    async def test_memory_retrieval_includes_correlation_id(
        self, memory_service, sample_memory_items
    ):
        """T129: Verify correlation_id is passed through and available for logging."""
        from uuid import uuid4

        correlation_id = uuid4()
        request = MemoryQueryRequest(
            user_id="test-user",
            query="test query",
        )

        with patch.object(
            memory_service.embedding_service, "get_embedding", return_value=[0.1] * 1536
        ):
            with patch.object(memory_service, "keyword_search", return_value=[]):
                with patch.object(memory_service, "semantic_search", return_value=[]):
                    with patch(
                        "src.services.memory_service.logger"
                    ) as mock_logger:
                        response = await memory_service.hybrid_search(
                            request, correlation_id=correlation_id
                        )

                        # Verify logger.info was called with correlation_id
                        mock_logger.info.assert_called()
                        call_kwargs = mock_logger.info.call_args.kwargs
                        assert call_kwargs["correlation_id"] == str(correlation_id)
