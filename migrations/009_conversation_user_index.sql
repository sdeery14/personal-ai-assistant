-- Migration 009: Add composite index on conversations for user + recency queries
-- Optimizes the common query pattern: fetch a user's conversations ordered by
-- most recently updated (e.g., sidebar conversation list in the web frontend).

CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
    ON conversations(user_id, updated_at DESC);
