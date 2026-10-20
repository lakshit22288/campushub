BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM branches WHERE code = 'CSE') THEN
    RAISE EXCEPTION 'Computer Science / IT branch (CSE) does not exist';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM notes
    JOIN subjects ON subjects.id = notes.subject_id
    JOIN branches ON branches.id = subjects.branch_id
    WHERE branches.code = 'CSE'
  ) THEN
    RAISE EXCEPTION 'Cannot replace CSE subjects while study notes are attached';
  END IF;
END $$;

UPDATE tools
SET subject_id = NULL
WHERE subject_id IN (
  SELECT subjects.id
  FROM subjects
  JOIN branches ON branches.id = subjects.branch_id
  WHERE branches.code = 'CSE'
);

DELETE FROM subjects
WHERE branch_id = (SELECT id FROM branches WHERE code = 'CSE');

INSERT INTO subjects (branch_id, name, slug)
SELECT branches.id, catalog.name, catalog.slug
FROM branches
CROSS JOIN (
  VALUES
    ('English', 'english'),
    ('Applied Mathematics', 'applied-mathematics'),
    ('Applied Physics', 'applied-physics'),
    ('Computer Fundamentals', 'computer-fundamentals'),
    ('Fundamental of Electrical and Electronics Engineering', 'fundamental-electrical-electronics-engineering'),
    ('Environmental Studies', 'environmental-studies'),
    ('Engineering Graphics', 'engineering-graphics'),
    ('Information Technology', 'information-technology'),
    ('Internet of Things & Artificial Intelligence', 'internet-of-things-artificial-intelligence'),
    ('General Workshop Practice', 'general-workshop-practice'),
    ('Programming in C', 'programming-c'),
    ('Operating Systems', 'operating-systems'),
    ('Digital Electronics', 'digital-electronics'),
    ('Multimedia Applications', 'multimedia-applications'),
    ('Data Communication', 'data-communication'),
    ('Data Structures Using C', 'data-structures-using-c'),
    ('Object Oriented Programming Using Java', 'object-oriented-programming-using-java'),
    ('Computer Organization', 'computer-organization'),
    ('Microprocessors & Peripheral Devices', 'microprocessors-peripheral-devices'),
    ('Database Management System', 'database-management-system'),
    ('Industrial Training', 'industrial-training'),
    ('Software Engineering', 'software-engineering'),
    ('Computer Networks', 'computer-networks'),
    ('Computer Programming Using Python', 'computer-programming-using-python'),
    ('Elective', 'elective'),
    ('Web Development Using PHP', 'web-development-using-php'),
    ('Network Security', 'network-security'),
    ('Mobile Application Development', 'mobile-application-development'),
    ('Application Development Using Web Framework', 'application-development-using-web-framework'),
    ('Entrepreneurship Development & Management', 'entrepreneurship-development-management')
) AS catalog(name, slug)
WHERE branches.code = 'CSE';

COMMIT;
