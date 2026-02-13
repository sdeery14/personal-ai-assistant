-- Migration 007: Create users table
-- Stores user accounts for authentication and authorization.
-- Supports local username/password auth with bcrypt password hashes.

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Reusable trigger function for auto-updating updated_at on any table.
-- Prior migrations (001) used table-specific functions; this generic version
-- can be shared across all tables going forward.
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Auto-update updated_at on row modification
DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Case-insensitive unique index on username for login lookups
-- Ensures 'Alice' and 'alice' cannot both exist
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_lower
    ON users(LOWER(username));
