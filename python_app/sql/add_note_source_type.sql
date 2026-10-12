BEGIN;

ALTER TABLE public.notes
  ADD COLUMN IF NOT EXISTS source_type TEXT NOT NULL DEFAULT 'teacher';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'notes_source_type_check'
      AND conrelid = 'public.notes'::regclass
  ) THEN
    ALTER TABLE public.notes
      ADD CONSTRAINT notes_source_type_check
      CHECK (source_type IN ('teacher', 'ai'));
  END IF;
END;
$$;

COMMIT;
