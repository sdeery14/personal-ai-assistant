-- Migration 003: Create memory_items table
-- Stores curated memory items (read-only in v1 - manually seeded)
-- Types: fact, preference, decision, note

CREATE TABLE IF NOT EXISTS memory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('fact', 'preference', 'decision', 'note')),
    embedding VECTOR(1536) NOT NULL,  -- text-embedding-3-small dimension
    source_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    importance FLOAT NOT NULL DEFAULT 0.5 CHECK (importance >= 0.0 AND importance <= 1.0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ  -- Soft delete for reversibility
);

-- Partial index for active (non-deleted) memories per user
CREATE INDEX IF NOT EXISTS idx_memory_items_user_id
    ON memory_items(user_id)
    WHERE deleted_at IS NULL;

-- IVFFlat index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_memory_items_embedding
    ON memory_items USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- GIN index for full-text search on memory content
CREATE INDEX IF NOT EXISTS idx_memory_items_content_fts
    ON memory_items USING gin (to_tsvector('english', content));

-- Composite index for filtering by type per user
CREATE INDEX IF NOT EXISTS idx_memory_items_type
    ON memory_items(user_id, type)
    WHERE deleted_at IS NULL;
