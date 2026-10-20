BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM branches WHERE code = 'EE') THEN
    RAISE EXCEPTION 'Electrical Engineering branch (EE) does not exist';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM notes
    JOIN subjects ON subjects.id = notes.subject_id
    JOIN branches ON branches.id = subjects.branch_id
    WHERE branches.code = 'EE'
  ) THEN
    RAISE EXCEPTION 'Cannot replace EE subjects while study notes are attached';
  END IF;
END $$;

UPDATE tools
SET subject_id = NULL
WHERE subject_id IN (
  SELECT subjects.id
  FROM subjects
  JOIN branches ON branches.id = subjects.branch_id
  WHERE branches.code = 'EE'
);

DELETE FROM subjects
WHERE branch_id = (SELECT id FROM branches WHERE code = 'EE');

INSERT INTO subjects (branch_id, name, slug)
SELECT branches.id, catalog.name, catalog.slug
FROM branches
CROSS JOIN (
  VALUES
    ('English', 'english'),
    ('Applied Mathematics', 'applied-mathematics'),
    ('Applied Physics', 'applied-physics'),
    ('Applied Chemistry', 'applied-chemistry'),
    ('Fundamental of Electrical and Electronics Engineering', 'fundamental-electrical-electronics-engineering'),
    ('Environmental Studies', 'environmental-studies'),
    ('Engineering Graphics', 'engineering-graphics'),
    ('Information Technology', 'information-technology'),
    ('Internet of Things & Artificial Intelligence', 'internet-of-things-artificial-intelligence'),
    ('General Workshop Practice', 'general-workshop-practice'),
    ('Student Centered Activities (SCA)', 'student-centered-activities-sca'),
    ('Non Conventional Sources of Energy', 'non-conventional-sources-of-energy'),
    ('Computer Applications in Electrical Engineering', 'computer-applications-electrical-engineering'),
    ('Electrical and Electronics Engineering Materials', 'electrical-electronics-engineering-materials'),
    ('Electronics II', 'electronics-ii'),
    ('Electrical Engineering Design and Drawing-I', 'electrical-engineering-design-drawing-i'),
    ('Electrical Workshop Practice - I', 'electrical-workshop-practice-i'),
    ('Estimating and Costing in Electrical Engineering', 'estimating-costing-electrical-engineering'),
    ('Electrical Machines - I', 'electrical-machines-i'),
    ('Electrical Measuring Instruments and Instrumentation', 'electrical-measuring-instruments-instrumentation'),
    ('Installation and Maintenance of Electrical Equipment', 'installation-maintenance-electrical-equipment'),
    ('Digital Electronics', 'digital-electronics'),
    ('Electrical Engineering Design & Drawing-II', 'electrical-engineering-design-drawing-ii'),
    ('Electrical Workshop Practice-II', 'electrical-workshop-practice-ii'),
    ('Industrial Training', 'industrial-training'),
    ('Electrical Machines - II', 'electrical-machines-ii'),
    ('Electrical Power - I', 'electrical-power-i'),
    ('Programmable Logic Controllers and Microcontrollers', 'programmable-logic-controllers-microcontrollers'),
    ('Elective', 'elective'),
    ('Utilization of Electrical Energy (UEE)', 'utilization-electrical-energy-uee'),
    ('Minor Project Work', 'minor-project-work'),
    ('Electrical Energy Conservation & Management', 'electrical-energy-conservation-management'),
    ('Electrical Power - II', 'electrical-power-ii'),
    ('Industrial Electronics and Control of Drives', 'industrial-electronics-control-drives'),
    ('Entrepreneurship Development and Management', 'entrepreneurship-development-management'),
    ('Major Project Work', 'major-project-work')
) AS catalog(name, slug)
WHERE branches.code = 'EE';

COMMIT;
