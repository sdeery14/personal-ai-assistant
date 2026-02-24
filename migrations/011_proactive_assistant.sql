-- Feature 011: Proactive Assistant ("The Alfred Engine")
-- Adds scheduled tasks, task runs, observed patterns, engagement events, and proactiveness settings

-- Scheduled tasks table
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    task_type VARCHAR(20) NOT NULL,
    schedule_cron VARCHAR(100),
    scheduled_at TIMESTAMPTZ,
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    tool_name VARCHAR(100) NOT NULL,
    tool_args JSONB NOT NULL DEFAULT '{}',
    prompt_template TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    source VARCHAR(20) NOT NULL DEFAULT 'user',
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    run_count INTEGER NOT NULL DEFAULT 0,
    fail_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_task_type CHECK (task_type IN ('one_time', 'recurring')),
    CONSTRAINT chk_task_status CHECK (status IN ('active', 'paused', 'cancelled', 'completed')),
    CONSTRAINT chk_task_source CHECK (source IN ('user', 'agent'))
);

-- Index for listing user's tasks
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_user_id
    ON scheduled_tasks (user_id);

-- Index for scheduler poll query (find due tasks)
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run
    ON scheduled_tasks (next_run_at)
    WHERE status = 'active' AND next_run_at IS NOT NULL;

-- Index for filtered list queries
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_user_status
    ON scheduled_tasks (user_id, status);

-- Auto-update updated_at trigger for scheduled_tasks
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_scheduled_tasks'
    ) THEN
        CREATE TRIGGER set_updated_at_scheduled_tasks
            BEFORE UPDATE ON scheduled_tasks
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Task runs table
CREATE TABLE IF NOT EXISTS task_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES scheduled_tasks(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    result TEXT,
    error TEXT,
    notification_id UUID REFERENCES notifications(id) ON DELETE SET NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    CONSTRAINT chk_run_status CHECK (status IN ('running', 'success', 'failed', 'retrying'))
);

-- Index for run history per task
CREATE INDEX IF NOT EXISTS idx_task_runs_task_id
    ON task_runs (task_id, started_at DESC);

-- Observed patterns table
CREATE TABLE IF NOT EXISTS observed_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pattern_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '[]',
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acted_on BOOLEAN NOT NULL DEFAULT FALSE,
    suggested_action TEXT,
    confidence FLOAT NOT NULL DEFAULT 0.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for listing user's patterns
CREATE INDEX IF NOT EXISTS idx_observed_patterns_user_id
    ON observed_patterns (user_id);

-- Index for filtering by type
CREATE INDEX IF NOT EXISTS idx_observed_patterns_user_type
    ON observed_patterns (user_id, pattern_type);

-- Index for finding actionable patterns (ready to suggest)
CREATE INDEX IF NOT EXISTS idx_observed_patterns_actionable
    ON observed_patterns (user_id)
    WHERE acted_on = FALSE AND occurrence_count >= 3;

-- Auto-update updated_at trigger for observed_patterns
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_observed_patterns'
    ) THEN
        CREATE TRIGGER set_updated_at_observed_patterns
            BEFORE UPDATE ON observed_patterns
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Engagement events table
CREATE TABLE IF NOT EXISTS engagement_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    suggestion_type VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    source VARCHAR(20) NOT NULL,
    context JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_engagement_action CHECK (action IN ('engaged', 'dismissed')),
    CONSTRAINT chk_engagement_source CHECK (source IN ('conversation', 'notification', 'schedule'))
);

-- Index for calibration queries (per-user, per-type)
CREATE INDEX IF NOT EXISTS idx_engagement_events_user_type
    ON engagement_events (user_id, suggestion_type, created_at DESC);

-- Index for aggregate engagement rate
CREATE INDEX IF NOT EXISTS idx_engagement_events_user_action
    ON engagement_events (user_id, action, created_at DESC);

-- Proactiveness settings table (one row per user)
CREATE TABLE IF NOT EXISTS proactiveness_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    global_level FLOAT NOT NULL DEFAULT 0.7,
    suppressed_types JSONB NOT NULL DEFAULT '[]',
    boosted_types JSONB NOT NULL DEFAULT '[]',
    user_override VARCHAR(20),
    is_onboarded BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_global_level CHECK (global_level >= 0.0 AND global_level <= 1.0),
    CONSTRAINT chk_user_override CHECK (user_override IS NULL OR user_override IN ('more', 'less'))
);

-- Auto-update updated_at trigger for proactiveness_settings
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_proactiveness_settings'
    ) THEN
        CREATE TRIGGER set_updated_at_proactiveness_settings
            BEFORE UPDATE ON proactiveness_settings
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;
