# Data Model: Web Frontend (008)

**Date**: 2026-02-13
**Branch**: `008-web-frontend`

## New Entities

### User (NEW TABLE)

Supports multi-user authentication with admin-provisioned accounts (FR-020 through FR-024).

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| username | VARCHAR(100) | UNIQUE, NOT NULL | Login identifier |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt hash |
| display_name | VARCHAR(255) | NOT NULL | Shown in UI |
| is_admin | BOOLEAN | NOT NULL, DEFAULT false | Can manage other users |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | Disabled accounts cannot log in |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, auto-trigger | |

**Validation rules**:
- Username: 3-100 chars, alphanumeric + underscore/hyphen, case-insensitive uniqueness
- Password: minimum 8 characters (enforced at API level, not DB)
- At least one admin user must exist at all times (enforced at application level)

**State transitions**:
- Created (is_active=true) → Disabled (is_active=false) → Deleted (hard delete)
- Admin cannot disable/delete themselves

### Refresh Token (NEW TABLE)

Supports JWT refresh token rotation for secure session management.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| user_id | UUID | FK → users, NOT NULL | |
| token_hash | VARCHAR(255) | UNIQUE, NOT NULL | SHA-256 hash of refresh token |
| expires_at | TIMESTAMPTZ | NOT NULL | 7-day default |
| revoked_at | TIMESTAMPTZ | nullable | Set when token is rotated or explicitly revoked |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Lifecycle**: Created on login → Rotated on refresh (old revoked, new issued) → Expired after TTL → Cleaned up periodically

## Modified Entities

### Conversation (EXISTING — modifications)

The existing `conversations` table already has `user_id`, `title`, `created_at`, `updated_at`. Changes needed:

| Change | Detail |
|--------|--------|
| `user_id` foreign key | Add FK constraint to `users.id` (currently unconstrained VARCHAR). Requires data migration to create user records for existing `user_id` values. |
| `title` population | Application logic: auto-generate title from first user message (truncate to ~80 chars). Allow user to update via PATCH endpoint. |
| Index | Add index on `(user_id, updated_at DESC)` for conversation list ordering. |

### Message (EXISTING — no schema changes)

No schema changes. Messages are already linked to conversations via `conversation_id` FK.

### Memory Item (EXISTING — no schema changes)

No schema changes. Already has `user_id` for scoping. The frontend reads and deletes via new REST endpoints but the underlying table is unchanged.

### Entity (EXISTING — no schema changes)

No schema changes. Already has `user_id` for scoping. The frontend reads via new REST endpoints.

### Relationship (EXISTING — no schema changes)

No schema changes. The frontend reads relationships via entity-scoped endpoints.

## Entity Relationship Diagram

```
User 1──* Conversation 1──* Message
 │
 ├──* MemoryItem (via user_id)
 ├──* Entity (via user_id)
 │       └──* Relationship (via source_entity_id / target_entity_id)
 └──* RefreshToken
```

## Migration Strategy

1. Create `users` table
2. Create `refresh_tokens` table
3. Create initial admin user (via first-run setup endpoint or migration script)
4. Add FK constraint from `conversations.user_id` to `users.id`
   - Requires creating user records for any existing `user_id` values in conversations
5. Add index on `conversations(user_id, updated_at DESC)`
