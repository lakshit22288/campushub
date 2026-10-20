BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM branches WHERE code = 'ECE') THEN
    RAISE EXCEPTION 'ECE branch does not exist';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM branches
    WHERE name = 'Electronics and Communication Engineering (ECE)'
      AND code <> 'ECE'
  ) THEN
    RAISE EXCEPTION 'The requested ECE branch name is already in use';
  END IF;
END $$;

UPDATE branches
SET name = 'Electronics and Communication Engineering (ECE)'
WHERE code = 'ECE';

COMMIT;
