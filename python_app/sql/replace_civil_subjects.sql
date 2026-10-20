BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM branches WHERE code = 'CE') THEN
    RAISE EXCEPTION 'Civil Engineering branch (CE) does not exist';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM notes
    JOIN subjects ON subjects.id = notes.subject_id
    JOIN branches ON branches.id = subjects.branch_id
    WHERE branches.code = 'CE'
  ) THEN
    RAISE EXCEPTION 'Cannot replace CE subjects while study notes are attached';
  END IF;
END $$;

UPDATE tools
SET subject_id = NULL
WHERE subject_id IN (
  SELECT subjects.id
  FROM subjects
  JOIN branches ON branches.id = subjects.branch_id
  WHERE branches.code = 'CE'
);

DELETE FROM subjects
WHERE branch_id = (SELECT id FROM branches WHERE code = 'CE');

INSERT INTO subjects (branch_id, name, slug)
SELECT branches.id, catalog.name, catalog.slug
FROM branches
CROSS JOIN (
  VALUES
    ('English', 'english'),
    ('Applied Mechanics', 'applied-mechanics'),
    ('Environmental Studies', 'environmental-studies'),
    ('Engineering Graphics', 'engineering-graphics'),
    ('Information Technology', 'information-technology'),
    ('Internet of Things & Artificial Intelligence', 'internet-of-things-artificial-intelligence'),
    ('General Workshop Practice', 'general-workshop-practice'),
    ('Student Centered Activities (SCA)', 'student-centered-activities-sca'),
    ('Fluid Mechanics', 'fluid-mechanics'),
    ('Structural Mechanics', 'structural-mechanics'),
    ('Surveying - I', 'surveying-i'),
    ('Construction Materials', 'construction-materials'),
    ('Building Construction', 'building-construction'),
    ('Building Drawing', 'building-drawing'),
    ('Concrete Technology', 'concrete-technology'),
    ('Water Supply & Waste Water Engineering', 'water-supply-waste-water-engineering'),
    ('Irrigation Engineering', 'irrigation-engineering'),
    ('Surveying - II', 'surveying-ii'),
    ('Soil Mechanics & Foundation Engineering', 'soil-mechanics-foundation-engineering'),
    ('Water Supply & Waste Water Engineering and Irrigation Engineering Drawing', 'water-supply-waste-water-engineering-irrigation-engineering-drawing'),
    ('Highway Engineering', 'highway-engineering'),
    ('Reinforced Cement Concrete Design & Drawing', 'reinforced-cement-concrete-design-drawing'),
    ('Survey Camp', 'survey-camp'),
    ('Computer Applications in Civil Engineering', 'computer-applications-civil-engineering'),
    ('Railways, Bridges & Tunnels', 'railways-bridges-tunnels'),
    ('Plumbing Services', 'plumbing-services'),
    ('Elective', 'elective'),
    ('Steel Structures Design and Drawing', 'steel-structures-design-drawing'),
    ('Earthquake Resistant Building Construction', 'earthquake-resistant-building-construction'),
    ('Quantity Surveying & Valuation', 'quantity-surveying-valuation'),
    ('Construction Management & Accounts', 'construction-management-accounts'),
    ('Major Project Work', 'major-project-work')
) AS catalog(name, slug)
WHERE branches.code = 'CE';

COMMIT;
