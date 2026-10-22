BEGIN;

CREATE TABLE IF NOT EXISTS help_request_replies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  help_request_id UUID NOT NULL REFERENCES help_requests(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  message TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_help_request_replies_request_created
  ON help_request_replies(help_request_id, created_at);

COMMIT;
