"""Integration tests for memory retrieval functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestHealthEndpointWithMemory:
    """Tests for health endpoint with memory infrastructure."""

    @pytest.mark.asyncio
    async def test_health_includes_database_status(self, async_client):
        """Test that health endpoint includes database status."""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "redis" in data

    @pytest.mark.asyncio
    async def test_health_graceful_when_database_unavailable(self, async_client):
        """Test health endpoint works even when database is unavailable."""
        with patch(
            "src.api.routes.db_health_check",
            side_effect=Exception("Connection failed"),
        ):
            response = await async_client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestChatEndpointWithMemory:
    """Tests for chat endpoint with memory features."""

    @pytest.mark.asyncio
    async def test_chat_accepts_user_id(self, async_client):
        """Test that chat endpoint accepts user_id parameter."""
        with patch("src.services.chat_service.ChatService") as mock_service_class:
            mock_service = MagicMock()

            async def mock_stream():
                from src.models.response import StreamChunk
                from uuid import uuid4

                yield StreamChunk(
                    content="Hello",
                    sequence=0,
                    is_final=False,
                    correlation_id=uuid4(),
                )
                yield StreamChunk(
                    content="",
                    sequence=1,
                    is_final=True,
                    correlation_id=uuid4(),
                )

            mock_service.stream_completion = mock_stream
            mock_service_class.return_value = mock_service

            response = await async_client.post(
                "/chat",
                json={
                    "message": "Hello",
                    "user_id": "test-user-123",
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_accepts_conversation_id(self, async_client):
        """Test that chat endpoint accepts conversation_id parameter."""
        with patch("src.services.chat_service.ChatService") as mock_service_class:
            mock_service = MagicMock()

            async def mock_stream():
                from src.models.response import StreamChunk
                from uuid import uuid4

                yield StreamChunk(
                    content="Hi",
                    sequence=0,
                    is_final=False,
                    correlation_id=uuid4(),
                )
                yield StreamChunk(
                    content="",
                    sequence=1,
                    is_final=True,
                    correlation_id=uuid4(),
                )

            mock_service.stream_completion = mock_stream
            mock_service_class.return_value = mock_service

            response = await async_client.post(
                "/chat",
                json={
                    "message": "Hello",
                    "user_id": "test-user",
                    "conversation_id": "12345678-1234-5678-1234-567812345678",
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_rejects_invalid_conversation_id(self, async_client):
        """Test that invalid conversation_id is rejected."""
        response = await async_client.post(
            "/chat",
            json={
                "message": "Hello",
                "conversation_id": "not-a-valid-uuid",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "conversation_id" in data.get("detail", "").lower()


class TestEmptyMemoryStore:
    """Tests for handling empty memory store gracefully."""

    @pytest.mark.asyncio
    async def test_empty_memory_store_no_errors(self, async_client):
        """Test that first-time user with no memories doesn't cause errors."""
        # This tests the graceful degradation when memory store is empty
        with patch("src.services.chat_service.ChatService") as mock_service_class:
            mock_service = MagicMock()
            mock_service._database_available = False

            async def mock_stream():
                from src.models.response import StreamChunk
                from uuid import uuid4

                yield StreamChunk(
                    content="Hello! I'm here to help.",
                    sequence=0,
                    is_final=False,
                    correlation_id=uuid4(),
                )
                yield StreamChunk(
                    content="",
                    sequence=1,
                    is_final=True,
                    correlation_id=uuid4(),
                )

            mock_service.stream_completion = mock_stream
            mock_service_class.return_value = mock_service

            response = await async_client.post(
                "/chat",
                json={
                    "message": "Hi, I'm new here",
                    "user_id": "brand-new-user",
                },
            )

            assert response.status_code == 200


class TestAgentToolInvocation:
    """Tests for Agent tool invocation (T093)."""

    @pytest.mark.asyncio
    async def test_agent_can_invoke_query_memory(self):
        """T093: Verify Agent can invoke query_memory tool.

        This test verifies that the query_memory tool is properly
        configured and can be invoked by the Agent.
        """
        from src.tools.query_memory import query_memory_tool
        from agents import FunctionTool

        # Verify the tool is a FunctionTool instance
        assert isinstance(query_memory_tool, FunctionTool)

        # Verify tool has the expected name
        assert query_memory_tool.name == "query_memory_tool"

        # Verify tool has the expected parameters in its schema
        schema = query_memory_tool.params_json_schema
        assert "properties" in schema
        assert "query" in schema["properties"]

    @pytest.mark.asyncio
    async def test_query_memory_tool_registered_with_agent(self):
        """Verify memory specialist is available in the orchestrator agent.

        The ChatService creates specialist sub-agents as tools. The memory
        specialist wraps query_memory, save_memory, and delete_memory tools.
        """
        from src.services.chat_service import ChatService

        with patch("src.services.chat_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                openai_api_key="test-key",
                openai_model="gpt-4",
                max_tokens=2000,
                timeout_seconds=30,
            )

            service = ChatService()
            service._database_available = True
            service._conversation_service = MagicMock()

            agent = service.create_agent()
            tool_names = [t.name for t in agent.tools]
            assert "ask_memory_agent" in tool_names, "ask_memory_agent should be registered"

    @pytest.mark.asyncio
    async def test_query_memory_tool_context_includes_user_id(self):
        """Verify user_id is passed in context when Agent invokes tool."""
        import json
        from unittest.mock import AsyncMock, patch
        from uuid import uuid4

        from src.services.memory_service import MemoryService
        from src.services.redis_service import RedisService

        # Mock dependencies
        with patch.object(
            RedisService, "check_rate_limit", return_value=(True, 9)
        ):
            with patch("src.services.memory_service.get_settings") as mock_mem_settings:
                mock_mem_settings.return_value = MagicMock(
                    token_budget=1000,
                    min_relevance=0.3,
                    max_results=10,
                    rrf_k=60,
                    openai_api_key="test-key",
                    embedding_model="text-embedding-3-small",
                )

                with patch.object(
                    MemoryService, "hybrid_search"
                ) as mock_search:
                    from src.models.memory import MemoryQueryResponse

                    mock_search.return_value = MemoryQueryResponse(
                        items=[],
                        total_count=0,
                        query_embedding_ms=10,
                        retrieval_ms=20,
                        token_count=0,
                        truncated=False,
                    )

                    # Import after mocking
                    from src.tools.query_memory import query_memory_tool

                    # Create mock context with user_id
                    mock_ctx = MagicMock()
                    mock_ctx.context = {
                        "user_id": "test-user-123",
                        "correlation_id": uuid4(),
                    }

                    # Call the tool function directly
                    # Note: We access the wrapped function via the tool
                    result = await query_memory_tool.on_invoke_tool(
                        mock_ctx,
                        '{"query": "test query"}',
                    )

                    # Verify hybrid_search was called
                    assert mock_search.called

                    # Verify the request included user_id
                    call_args = mock_search.call_args
                    request = call_args.kwargs.get("request") or call_args[0][0]
                    assert request.user_id == "test-user-123"
