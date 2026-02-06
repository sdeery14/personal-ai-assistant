-- Migration 006: Knowledge Graph schema
-- Creates entities and entity_relationships tables for tracking
-- people, projects, tools, concepts, and their relationships.

-- =============================================================================
-- ENTITIES TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,

    -- Entity identification
    name VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255) NOT NULL,  -- lowercase, normalized for dedup
    type VARCHAR(20) NOT NULL,
    aliases TEXT[] DEFAULT '{}',
    description TEXT,

    -- Embedding for semantic search
    embedding VECTOR(1536),  -- text-embedding-3-small dimension

    -- Extraction metadata
    confidence FLOAT DEFAULT 1.0,
    mention_count INTEGER DEFAULT 1,

    -- Provenance
    first_seen_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    first_seen_conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    last_mentioned_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT entities_type_check CHECK (type IN ('person', 'project', 'tool', 'concept', 'organization')),
    CONSTRAINT entities_confidence_check CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

-- Unique constraint: one entity per name+type per user (for non-deleted)
CREATE UNIQUE INDEX IF NOT EXISTS idx_entities_unique_per_user
    ON entities(user_id, canonical_name, type)
    WHERE deleted_at IS NULL;

-- Index for user scoping (partial: non-deleted only)
CREATE INDEX IF NOT EXISTS idx_entities_user_id
    ON entities(user_id)
    WHERE deleted_at IS NULL;

-- Index for filtering by user + type
CREATE INDEX IF NOT EXISTS idx_entities_user_type
    ON entities(user_id, type)
    WHERE deleted_at IS NULL;

-- Index for canonical name lookups (deduplication)
CREATE INDEX IF NOT EXISTS idx_entities_canonical_name
    ON entities(user_id, canonical_name)
    WHERE deleted_at IS NULL;

-- IVFFlat index for vector similarity search on entity embeddings
CREATE INDEX IF NOT EXISTS idx_entities_embedding
    ON entities USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- =============================================================================
-- ENTITY RELATIONSHIPS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS entity_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,

    -- Relationship endpoints
    source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,  -- nullable for user-centric relationships

    -- Relationship metadata
    relationship_type VARCHAR(30) NOT NULL,
    context TEXT,  -- additional context about the relationship
    confidence FLOAT DEFAULT 1.0,

    -- Provenance
    source_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    source_conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT relationships_type_check CHECK (relationship_type IN (
        'USES', 'PREFERS', 'DECIDED', 'WORKS_ON', 'WORKS_WITH',
        'KNOWS', 'DEPENDS_ON', 'MENTIONED_IN', 'PART_OF'
    )),
    CONSTRAINT relationships_confidence_check CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

-- Index for user scoping
CREATE INDEX IF NOT EXISTS idx_relationships_user_id
    ON entity_relationships(user_id)
    WHERE deleted_at IS NULL;

-- Index for graph traversal from source entity
CREATE INDEX IF NOT EXISTS idx_relationships_source
    ON entity_relationships(source_entity_id)
    WHERE deleted_at IS NULL;

-- Index for reverse graph traversal to target entity
CREATE INDEX IF NOT EXISTS idx_relationships_target
    ON entity_relationships(target_entity_id)
    WHERE deleted_at IS NULL;

-- Index for filtering by relationship type
CREATE INDEX IF NOT EXISTS idx_relationships_type
    ON entity_relationships(user_id, relationship_type)
    WHERE deleted_at IS NULL;

-- Composite index for checking existing relationships (deduplication)
CREATE INDEX IF NOT EXISTS idx_relationships_dedup
    ON entity_relationships(user_id, source_entity_id, target_entity_id, relationship_type)
    WHERE deleted_at IS NULL;
