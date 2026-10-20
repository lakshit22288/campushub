BEGIN;

DO $$
DECLARE
  required_codes TEXT[] := ARRAY['CSE', 'CE', 'EE', 'ECE', 'ME', 'MLT'];
BEGIN
  IF EXISTS (
    SELECT code FROM unnest(required_codes) AS required(code)
    EXCEPT
    SELECT code FROM branches
  ) THEN
    RAISE EXCEPTION 'One or more required branches are missing';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM notes
    JOIN subjects ON subjects.id = notes.subject_id
    JOIN branches ON branches.id = subjects.branch_id
    WHERE branches.code = ANY(required_codes)
  ) THEN
    RAISE EXCEPTION 'Cannot replace branch subjects while study notes are attached';
  END IF;
END $$;

UPDATE tools
SET subject_id = NULL
WHERE subject_id IN (
  SELECT subjects.id
  FROM subjects
  JOIN branches ON branches.id = subjects.branch_id
  WHERE branches.code IN ('CSE', 'CE', 'EE', 'ECE', 'ME', 'MLT')
);

DELETE FROM subjects
WHERE branch_id IN (
  SELECT id FROM branches WHERE code IN ('CSE', 'CE', 'EE', 'ECE', 'ME', 'MLT')
);

WITH catalog(code, name, slug) AS (
  VALUES
    ('CSE', 'Computer Fundamentals', 'computer-fundamentals'),
    ('CSE', 'Programming in C', 'programming-in-c'),
    ('CSE', 'Operating Systems', 'operating-systems'),
    ('CSE', 'Multimedia Applications', 'multimedia-applications'),
    ('CSE', 'Data Communication', 'data-communication'),
    ('CSE', 'Data Structures Using C', 'data-structures-using-c'),
    ('CSE', 'Object Oriented Programming Using Java', 'object-oriented-programming-using-java'),
    ('CSE', 'Computer Organization', 'computer-organization'),
    ('CSE', 'Database Management System', 'database-management-system'),
    ('CSE', 'Software Engineering', 'software-engineering'),
    ('CSE', 'Computer Programming Using Python', 'computer-programming-using-python'),
    ('CSE', 'Web Development Using PHP', 'web-development-using-php'),
    ('CSE', 'Network Security', 'network-security'),
    ('CSE', 'Mobile Application Development', 'mobile-application-development'),
    ('CSE', 'Application Development Using Web Framework', 'application-development-using-web-framework'),
    ('CSE', 'Applied Mathematics', 'applied-mathematics'),
    ('CSE', 'Applied Physics', 'applied-physics'),
    ('CSE', 'Information Technology', 'information-technology'),
    ('CSE', 'Internet of Things & Artificial Intelligence', 'internet-of-things-artificial-intelligence'),
    ('CSE', 'Digital Electronics', 'digital-electronics'),
    ('CSE', 'Fundamental of Electrical and Electronics Engineering', 'fundamental-electrical-and-electronics-engineering'),
    ('CSE', 'Computer Networks', 'computer-networks'),
    ('CSE', 'Microprocessor and Peripheral Devices', 'microprocessor-and-peripheral-devices'),
    ('CE', 'Applied Mechanics', 'applied-mechanics'),
    ('CE', 'Fluid Mechanics', 'fluid-mechanics'),
    ('CE', 'Structural Mechanics', 'structural-mechanics'),
    ('CE', 'Surveying - I', 'surveying-i'),
    ('CE', 'Construction Materials', 'construction-materials'),
    ('CE', 'Building Construction', 'building-construction'),
    ('CE', 'Building Drawing', 'building-drawing'),
    ('CE', 'Concrete Technology', 'concrete-technology'),
    ('CE', 'Water Supply & Waste Water Engineering', 'water-supply-and-waste-water-engineering'),
    ('CE', 'Irrigation Engineering', 'irrigation-engineering'),
    ('CE', 'Surveying - II', 'surveying-ii'),
    ('CE', 'Soil Mechanics & Foundation Engineering', 'soil-mechanics-and-foundation-engineering'),
    ('CE', 'Highway Engineering', 'highway-engineering'),
    ('CE', 'Reinforced Cement Concrete Design & Drawing', 'reinforced-cement-concrete-design-and-drawing'),
    ('CE', 'Railways, Bridges & Tunnels', 'railways-bridges-and-tunnels'),
    ('CE', 'Plumbing Services', 'plumbing-services'),
    ('CE', 'Steel Structures Design and Drawing', 'steel-structures-design-and-drawing'),
    ('CE', 'Earthquake Resistant Building Construction', 'earthquake-resistant-building-construction'),
    ('CE', 'Quantity Surveying & Valuation', 'quantity-surveying-and-valuation'),
    ('CE', 'Construction Management & Accounts', 'construction-management-and-accounts'),
    ('CE', 'Applied Mathematics', 'applied-mathematics'),
    ('CE', 'Applied Physics', 'applied-physics'),
    ('CE', 'Information Technology', 'information-technology'),
    ('CE', 'Internet of Things & Artificial Intelligence', 'internet-of-things-and-artificial-intelligence'),
    ('CE', 'Elective', 'elective'),
    ('CE', 'Computer Applications in Civil Engineering', 'computer-applications-in-civil-engineering'),

    ('EE', 'Non Conventional Sources of Energy', 'non-conventional-sources-of-energy'),
    ('EE', 'Electrical and Electronics Engineering Materials', 'electrical-and-electronics-engineering-materials'),
    ('EE', 'Electronics II', 'electronics-ii'),
    ('EE', 'Electrical Engineering Design and Drawing - I', 'electrical-engineering-design-and-drawing-i'),
    ('EE', 'Electrical Machines - I', 'electrical-machines-i'),
    ('EE', 'Electrical Measuring Instruments and Instrumentation', 'electrical-measuring-instruments-and-instrumentation'),
    ('EE', 'Installation and Maintenance of Electrical Equipment', 'installation-and-maintenance-of-electrical-equipment'),
    ('EE', 'Electrical Engineering Design & Drawing - II', 'electrical-engineering-design-and-drawing-ii'),
    ('EE', 'Electrical Machines - II', 'electrical-machines-ii'),
    ('EE', 'Electrical Power - I', 'electrical-power-i'),
    ('EE', 'Programmable Logic Controllers and Microcontrollers', 'programmable-logic-controllers-and-microcontrollers'),
    ('EE', 'Utilization of Electrical Energy', 'utilization-of-electrical-energy'),
    ('EE', 'Electrical Energy Conservation & Management', 'electrical-energy-conservation-and-management'),
    ('EE', 'Electrical Power - II', 'electrical-power-ii'),
    ('EE', 'Industrial Electronics and Control of Drives', 'industrial-electronics-and-control-of-drives'),
    ('EE', 'Applied Mathematics', 'applied-mathematics'),
    ('EE', 'Applied Physics', 'applied-physics'),
    ('EE', 'Information Technology', 'information-technology'),
    ('EE', 'Internet of Things & Artificial Intelligence', 'internet-of-things-and-artificial-intelligence'),
    ('EE', 'Digital Electronics', 'digital-electronics'),
    ('EE', 'Fundamental of Electrical and Electronics Engineering', 'fundamental-of-electrical-and-electronics-engineering'),
    ('EE', 'Elective', 'elective'),
    ('EE', 'Computer Applications in Electrical Engineering', 'computer-applications-in-electrical-engineering'),

    ('ECE', 'Electronic Instruments and Measurement', 'electronic-instruments-and-measurement'),
    ('ECE', 'Principles of Communication Engineering', 'principles-of-communication-engineering'),
    ('ECE', 'Electronic Devices and Circuits', 'electronic-devices-and-circuits'),
    ('ECE', 'Network Filters and Transmission Lines', 'network-filters-and-transmission-lines'),
    ('ECE', 'Instrumentation', 'instrumentation'),
    ('ECE', 'Communication System', 'communication-system'),
    ('ECE', 'Troubleshooting of Electronic Equipment', 'troubleshooting-of-electronic-equipment'),
    ('ECE', 'Medical Electronics', 'medical-electronics'),
    ('ECE', 'Audio Video Systems', 'audio-video-systems'),
    ('ECE', 'Digital Communication', 'digital-communication'),
    ('ECE', 'Optical Fiber Communication', 'optical-fiber-communication'),
    ('ECE', 'Electronics Design and Simulation Techniques', 'electronics-design-and-simulation-techniques'),
    ('ECE', 'Microwave and Radar Engineering', 'microwave-and-radar-engineering'),
    ('ECE', 'Wireless and Mobile Communication', 'wireless-and-mobile-communication'),
    ('ECE', 'Applied Mathematics', 'applied-mathematics'),
    ('ECE', 'Applied Physics', 'applied-physics'),
    ('ECE', 'Information Technology', 'information-technology'),
    ('ECE', 'Internet of Things & Artificial Intelligence', 'internet-of-things-and-artificial-intelligence'),
    ('ECE', 'Digital Electronics', 'digital-electronics'),
    ('ECE', 'Fundamental of Electrical and Electronics Engineering', 'fundamental-of-electrical-and-electronics-engineering'),
    ('ECE', 'Computer Networks', 'computer-networks'),
    ('ECE', 'Microprocessor and Peripheral Devices', 'microprocessor-and-peripheral-devices'),
    ('ECE', 'Elective', 'elective'),

    ('ME', 'Strength of Materials', 'strength-of-materials'),
    ('ME', 'Thermodynamics - I', 'thermodynamics-i'),
    ('ME', 'Mechanical Engineering Drawing', 'mechanical-engineering-drawing'),
    ('ME', 'Computer Aided Drafting', 'computer-aided-drafting'),
    ('ME', 'Materials and Metallurgy', 'materials-and-metallurgy'),
    ('ME', 'Hydraulics and Pneumatics', 'hydraulics-and-pneumatics'),
    ('ME', 'Thermodynamics - II', 'thermodynamics-ii'),
    ('ME', 'Industrial Engineering', 'industrial-engineering'),
    ('ME', 'Theory of Machines', 'theory-of-machines'),
    ('ME', 'Refrigeration and Air-conditioning', 'refrigeration-and-air-conditioning'),
    ('ME', 'Machine Design', 'machine-design'),
    ('ME', 'CNC Machines and Automation', 'cnc-machines-and-automation'),
    ('ME', 'Automobile Engineering', 'automobile-engineering'),
    ('ME', 'Inspection and Quality Control', 'inspection-and-quality-control'),
    ('ME', 'Estimation and Costing', 'estimation-and-costing'),
    ('ME', 'Applied Mathematics', 'applied-mathematics'),
    ('ME', 'Applied Physics', 'applied-physics'),
    ('ME', 'Information Technology', 'information-technology'),
    ('ME', 'Internet of Things & Artificial Intelligence', 'internet-of-things-and-artificial-intelligence'),
    ('ME', 'Elective', 'elective'),

    ('MLT', 'Anatomy and Physiology', 'anatomy-and-physiology'),
    ('MLT', 'Clinical Microbiology', 'clinical-microbiology'),
    ('MLT', 'Haematology', 'haematology'),
    ('MLT', 'Clinical Biochemistry', 'clinical-biochemistry'),
    ('MLT', 'Clinical Microbiology - III', 'clinical-microbiology-iii'),
    ('MLT', 'Haematology - III', 'haematology-iii'),
    ('MLT', 'Clinical Biochemistry - III', 'clinical-biochemistry-iii'),
    ('MLT', 'Histopathology & Cytology - I', 'histopathology-and-cytology-i'),
    ('MLT', 'Transfusion Medicine (Blood Banking)', 'transfusion-medicine-blood-banking'),
    ('MLT', 'Clinical Microbiology - IV', 'clinical-microbiology-iv'),
    ('MLT', 'Haematology - IV', 'haematology-iv'),
    ('MLT', 'Clinical Biochemistry - IV', 'clinical-biochemistry-iv'),
    ('MLT', 'Histopathology & Cytology - II', 'histopathology-and-cytology-ii'),
    ('MLT', 'Medical Laboratory Management', 'medical-laboratory-management')
),
shared_subjects AS (
  SELECT name
  FROM catalog
  GROUP BY name
  HAVING COUNT(DISTINCT code) > 1
)
INSERT INTO subjects (branch_id, name, slug)
SELECT
  branches.id,
  CASE
    WHEN shared_subjects.name IS NOT NULL THEN catalog.name || ' (' || catalog.code || ')'
    ELSE catalog.name
  END,
  catalog.slug
FROM branches
JOIN catalog ON catalog.code = branches.code
LEFT JOIN shared_subjects ON shared_subjects.name = catalog.name
WHERE branches.code IN ('CSE', 'CE', 'EE', 'ECE', 'ME', 'MLT');

COMMIT;
