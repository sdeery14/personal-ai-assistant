-- Feature 010: Agent Notifications
-- Adds notification infrastructure: notifications table, preferences, deferred emails, and email column on users

-- Add email column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255);

-- Create unique index on email (partial - only non-null values)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (email) WHERE email IS NOT NULL;

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    message VARCHAR(500) NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'info',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    dismissed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_notification_type CHECK (type IN ('reminder', 'info', 'warning'))
);

-- Primary list query index (user's notifications in reverse chronological order)
CREATE INDEX IF NOT EXISTS idx_notifications_user_id_created_at
    ON notifications (user_id, created_at DESC);

-- Partial index for unread count query
CREATE INDEX IF NOT EXISTS idx_notifications_user_id_unread
    ON notifications (user_id)
    WHERE is_read = FALSE AND dismissed_at IS NULL;

-- Notification preferences table (one row per user)
CREATE TABLE IF NOT EXISTS notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    delivery_channel VARCHAR(20) NOT NULL DEFAULT 'in_app',
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    quiet_hours_timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_delivery_channel CHECK (delivery_channel IN ('in_app', 'email', 'both'))
);

-- Auto-update updated_at trigger for notification_preferences
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'set_updated_at_notification_preferences'
    ) THEN
        CREATE TRIGGER set_updated_at_notification_preferences
            BEFORE UPDATE ON notification_preferences
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Deferred emails table (for quiet hours deferral)
CREATE TABLE IF NOT EXISTS deferred_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    deliver_after TIMESTAMPTZ NOT NULL,
    delivered_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partial index for pending deferred emails
CREATE INDEX IF NOT EXISTS idx_deferred_emails_pending
    ON deferred_emails (deliver_after)
    WHERE delivered_at IS NULL AND failed_at IS NULL;
