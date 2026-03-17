CREATE TABLE IF NOT EXISTS chat_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(128) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NULL,
    metadata JSONB NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_pk BIGINT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    turn_index INTEGER NOT NULL,
    role VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_chat_messages_session_turn
    ON chat_messages(session_pk, turn_index);

CREATE INDEX IF NOT EXISTS ix_chat_sessions_expires_at
    ON chat_sessions(expires_at);
