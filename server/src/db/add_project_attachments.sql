BEGIN;

ALTER TABLE public.projects
  ADD COLUMN IF NOT EXISTS attachment_url TEXT,
  ADD COLUMN IF NOT EXISTS attachment_name TEXT;

COMMIT;
