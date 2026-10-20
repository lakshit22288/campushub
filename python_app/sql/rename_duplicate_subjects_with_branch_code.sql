BEGIN;

UPDATE subjects
SET name = subjects.name || ' (' || branches.code || ')'
FROM branches
WHERE subjects.branch_id = branches.id
  AND branches.code IN ('CSE', 'CE', 'EE', 'ECE', 'ME', 'MLT')
  AND (
    (subjects.name = 'Applied Mathematics' AND branches.code IN ('CSE', 'CE', 'EE', 'ECE', 'ME'))
    OR (subjects.name = 'Applied Physics' AND branches.code IN ('CSE', 'CE', 'EE', 'ECE', 'ME'))
    OR (subjects.name = 'Computer Networks' AND branches.code IN ('CSE', 'ECE'))
    OR (subjects.name = 'Digital Electronics' AND branches.code IN ('CSE', 'EE', 'ECE'))
    OR (subjects.name = 'Elective' AND branches.code IN ('CE', 'EE', 'ECE', 'ME'))
    OR (
      subjects.name = 'Fundamental of Electrical and Electronics Engineering'
      AND branches.code IN ('CSE', 'EE', 'ECE')
    )
    OR (subjects.name = 'Information Technology' AND branches.code IN ('CSE', 'CE', 'EE', 'ECE', 'ME'))
    OR (
      subjects.name = 'Internet of Things & Artificial Intelligence'
      AND branches.code IN ('CSE', 'CE', 'EE', 'ECE', 'ME')
    )
    OR (subjects.name = 'Microprocessor and Peripheral Devices' AND branches.code IN ('CSE', 'ECE'))
  );

COMMIT;
