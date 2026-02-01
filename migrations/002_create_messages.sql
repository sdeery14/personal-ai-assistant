-- Migration 002: Create messages table
-- Stores individual turns in conversations with embeddings for semantic search

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- text-embedding-3-small dimension
    correlation_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for conversation message retrieval
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);

-- Index for correlation ID lookup (debugging/tracing)
CREATE INDEX IF NOT EXISTS idx_messages_correlation_id ON messages(correlation_id);

-- IVFFlat index for vector similarity search (cosine distance)
-- lists=100 is suitable for up to ~100k rows; adjust for larger datasets
CREATE INDEX IF NOT EXISTS idx_messages_embedding
    ON messages USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- GIN index for full-text search
CREATE INDEX IF NOT EXISTS idx_messages_content_fts
    ON messages USING gin (to_tsvector('english', content));
