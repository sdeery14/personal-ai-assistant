-- Migration 004: Seed test memory items for user 'test-user'
-- These are manually seeded for testing; automatic extraction is v2 scope
--
-- NOTE: Embeddings are placeholder zeros - they will be generated on first query
-- or can be populated via a separate script using the embedding service.
-- For testing, we use all-zeros which will still work with cosine similarity.

-- Create a test conversation first (for source_message_id references)
INSERT INTO conversations (id, user_id, title, created_at)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'test-user', 'Initial Setup', NOW())
ON CONFLICT (id) DO NOTHING;

-- Insert a test message
INSERT INTO messages (id, conversation_id, role, content, correlation_id, created_at)
VALUES
    ('00000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000001', 'user', 'I prefer uv over pip for Python dependency management', '00000000-0000-0000-0000-000000000100', NOW())
ON CONFLICT (id) DO NOTHING;

-- Seed test memory items with various types
-- Using a zero vector as placeholder (1536 dimensions for text-embedding-3-small)
DO $$
DECLARE
    zero_embedding vector(1536) := array_fill(0::float, ARRAY[1536])::vector;
BEGIN
    -- Preference: Package manager
    INSERT INTO memory_items (id, user_id, content, type, embedding, source_message_id, importance, created_at)
    VALUES (
        '10000000-0000-0000-0000-000000000001',
        'test-user',
        'User prefers uv over pip for Python dependency management',
        'preference',
        zero_embedding,
        '00000000-0000-0000-0000-000000000010',
        0.8,
        NOW()
    )
    ON CONFLICT (id) DO NOTHING;

    -- Fact: Tech stack
    INSERT INTO memory_items (id, user_id, content, type, embedding, importance, created_at)
    VALUES (
        '10000000-0000-0000-0000-000000000002',
        'test-user',
        'Project stack includes FastAPI, Docker, and Postgres with pgvector',
        'fact',
        zero_embedding,
        0.7,
        NOW()
    )
    ON CONFLICT (id) DO NOTHING;

    -- Decision: Architecture choice
    INSERT INTO memory_items (id, user_id, content, type, embedding, importance, created_at)
    VALUES (
        '10000000-0000-0000-0000-000000000003',
        'test-user',
        'Decided to use hybrid search (keyword + semantic) with RRF fusion for memory retrieval',
        'decision',
        zero_embedding,
        0.9,
        NOW()
    )
    ON CONFLICT (id) DO NOTHING;

    -- Note: Context
    INSERT INTO memory_items (id, user_id, content, type, embedding, importance, created_at)
    VALUES (
        '10000000-0000-0000-0000-000000000004',
        'test-user',
        'Working on a personal AI assistant project with streaming chat and memory capabilities',
        'note',
        zero_embedding,
        0.5,
        NOW()
    )
    ON CONFLICT (id) DO NOTHING;

    -- Preference: Coding style
    INSERT INTO memory_items (id, user_id, content, type, embedding, importance, created_at)
    VALUES (
        '10000000-0000-0000-0000-000000000005',
        'test-user',
        'User prefers type hints and async/await patterns in Python code',
        'preference',
        zero_embedding,
        0.7,
        NOW()
    )
    ON CONFLICT (id) DO NOTHING;

    -- Fact: Environment
    INSERT INTO memory_items (id, user_id, content, type, embedding, importance, created_at)
    VALUES (
        '10000000-0000-0000-0000-000000000006',
        'test-user',
        'Development environment is Windows with WSL2 support',
        'fact',
        zero_embedding,
        0.5,
        NOW()
    )
    ON CONFLICT (id) DO NOTHING;

    -- Preference: Testing
    INSERT INTO memory_items (id, user_id, content, type, embedding, importance, created_at)
    VALUES (
        '10000000-0000-0000-0000-000000000007',
        'test-user',
        'User prefers pytest for testing with high coverage requirements',
        'preference',
        zero_embedding,
        0.6,
        NOW()
    )
    ON CONFLICT (id) DO NOTHING;

    -- Another user's memory (for cross-user security testing)
    INSERT INTO memory_items (id, user_id, content, type, embedding, importance, created_at)
    VALUES (
        '20000000-0000-0000-0000-000000000001',
        'other-user',
        'This is a secret memory that should never be retrieved by test-user',
        'note',
        zero_embedding,
        1.0,
        NOW()
    )
    ON CONFLICT (id) DO NOTHING;
END $$;
