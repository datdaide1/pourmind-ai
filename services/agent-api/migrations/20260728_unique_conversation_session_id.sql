BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT session_id FROM conversations
        GROUP BY session_id HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Duplicate conversations.session_id values must be resolved before migration';
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS ix_conversations_session_id
    ON conversations (session_id);

COMMIT;
