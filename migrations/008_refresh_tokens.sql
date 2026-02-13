-- Migration 008: Create refresh_tokens table
-- Stores hashed refresh tokens for JWT-based authentication.
-- Tokens are hashed (SHA-256) before storage; raw tokens are never persisted.

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,  -- NULL = active, set on revocation
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for looking up all tokens belonging to a user (logout-all, admin)
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id
    ON refresh_tokens(user_id);

-- Index for token validation lookups by hash
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash
    ON refresh_tokens(token_hash);

-- Partial index for expired-token cleanup jobs (only non-revoked tokens)
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at_active
    ON refresh_tokens(expires_at)
    WHERE revoked_at IS NULL;
