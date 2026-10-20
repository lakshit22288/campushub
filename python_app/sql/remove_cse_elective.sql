BEGIN;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM notes
    JOIN subjects ON subjects.id = notes.subject_id
    JOIN branches ON branches.id = subjects.branch_id
    WHERE branches.code = 'CSE' AND subjects.slug = 'elective'
  ) THEN
    RAISE EXCEPTION 'Cannot remove CSE Elective while study notes are attached';
  END IF;
END $$;

UPDATE tools
SET subject_id = NULL
WHERE subject_id IN (
  SELECT subjects.id
  FROM subjects
  JOIN branches ON branches.id = subjects.branch_id
  WHERE branches.code = 'CSE' AND subjects.slug = 'elective'
);

DELETE FROM subjects
USING branches
WHERE subjects.branch_id = branches.id
  AND branches.code = 'CSE'
  AND subjects.slug = 'elective';

COMMIT;
