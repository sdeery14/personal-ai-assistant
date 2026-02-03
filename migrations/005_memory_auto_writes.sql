-- Migration 005: Memory auto writes schema extensions
-- Adds columns for agent-driven memory extraction and audit logging

-- Add source_conversation_id to track which conversation generated a memory
ALTER TABLE memory_items ADD COLUMN IF NOT EXISTS source_conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL;

-- Add confidence score for extraction confidence
ALTER TABLE memory_items ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0);

-- Add superseded_by for memory correction/update chains
ALTER TABLE memory_items ADD COLUMN IF NOT EXISTS superseded_by UUID REFERENCES memory_items(id) ON DELETE SET NULL;

-- Add status for memory lifecycle tracking
ALTER TABLE memory_items ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'deleted'));

-- Drop and recreate type constraint to add 'episode'
-- First remove the old constraint (name may vary by DB)
DO $$
BEGIN
    ALTER TABLE memory_items DROP CONSTRAINT IF EXISTS memory_items_type_check;
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

ALTER TABLE memory_items ADD CONSTRAINT memory_items_type_check
    CHECK (type IN ('fact', 'preference', 'decision', 'note', 'episode'));

-- Index on superseded_by for correction chain lookups
CREATE INDEX IF NOT EXISTS idx_memory_items_superseded_by
    ON memory_items(superseded_by)
    WHERE superseded_by IS NOT NULL;

-- Index on status for filtering active memories
CREATE INDEX IF NOT EXISTS idx_memory_items_status
    ON memory_items(user_id, status)
    WHERE status = 'active';

-- Audit table for memory write operations
CREATE TABLE IF NOT EXISTS memory_write_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_item_id UUID REFERENCES memory_items(id) ON DELETE SET NULL,
    user_id VARCHAR(255) NOT NULL,
    operation VARCHAR(20) NOT NULL CHECK (operation IN ('create', 'delete', 'supersede', 'episode')),
    confidence FLOAT CHECK (confidence >= 0.0 AND confidence <= 1.0),
    extraction_type VARCHAR(20) CHECK (extraction_type IN ('agent', 'episode', 'manual')),
    before_content TEXT,
    after_content TEXT,
    correlation_id UUID,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for audit log lookups by user
CREATE INDEX IF NOT EXISTS idx_memory_write_events_user_id
    ON memory_write_events(user_id, created_at DESC);

-- Index for audit log lookups by memory item
CREATE INDEX IF NOT EXISTS idx_memory_write_events_memory_item_id
    ON memory_write_events(memory_item_id);
