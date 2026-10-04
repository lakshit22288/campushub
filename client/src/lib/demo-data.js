export const demoBranches = [
  { id: 1, code: 'CSE', name: 'Computer Science' },
  { id: 2, code: 'ME', name: 'Mechanical' },
  { id: 3, code: 'EE', name: 'Electrical' },
  { id: 4, code: 'ECE', name: 'Electronics' },
  { id: 5, code: 'CE', name: 'Civil' },
  { id: 6, code: 'MLT', name: 'Medical Lab Technology' }
]

export const demoSubjects = [
  { id: 101, branch_id: 1, code: 'CSE', name: 'Operating System', slug: 'operating-system' },
  { id: 102, branch_id: 1, code: 'CSE', name: 'DBMS', slug: 'dbms' },
  { id: 103, branch_id: 1, code: 'CSE', name: 'Web Development', slug: 'web-development' },
  { id: 104, branch_id: 2, code: 'ME', name: 'Thermodynamics', slug: 'thermodynamics' },
  { id: 105, branch_id: 3, code: 'EE', name: 'Electrical Circuits', slug: 'electrical-circuits' },
  { id: 106, branch_id: 4, code: 'ECE', name: 'Digital Electronics', slug: 'digital-electronics' },
  { id: 107, branch_id: 5, code: 'CE', name: 'Surveying', slug: 'surveying' },
  { id: 108, branch_id: 6, code: 'MLT', name: 'Clinical Biochemistry', slug: 'clinical-biochemistry' }
]

export const demoTools = [
  { id: 201, name: 'Percentage Calculator', description: 'Compute marks percentages quickly.', category: 'Academic', route: '/tools/percentage', branch_id: null },
  { id: 202, name: 'CGPA Calculator', description: 'Average semester performance instantly.', category: 'Academic', route: '/tools/cgpa', branch_id: null },
  { id: 203, name: 'Unit Converter', description: 'Convert common study and engineering units.', category: 'Academic', route: '/tools/units', branch_id: null },
  { id: 204, name: "Ohm's Law Calculator", description: 'Solve voltage, current and resistance relationships.', category: 'Electrical', route: '/tools/ohms-law', branch_id: 3 },
  { id: 205, name: 'Power Calculator', description: 'Calculate electrical power with ease.', category: 'Electrical', route: '/tools/power', branch_id: 3 },
  { id: 206, name: 'Logic Gate Helper', description: 'Practice AND, OR, NOT and basic Boolean operations.', category: 'Electronics', route: '/tools/logic-gates', branch_id: 4 },
  { id: 207, name: 'Linux Command Helper', description: 'Search common Linux commands and examples.', category: 'Systems', route: '/tools/linux', branch_id: 1 },
  { id: 208, name: 'Python Playground', description: 'Practice Python expressions and core concepts.', category: 'Coding', route: '/tools/python', branch_id: 1 },
  { id: 209, name: 'SQL Query Practice', description: 'Practice and format SQL queries without executing them.', category: 'Database', route: '/tools/sql', branch_id: 1 },
  { id: 210, name: 'IP/Subnet Calculator', description: 'Calculate IPv4 network ranges from an address and CIDR prefix.', category: 'Networking', route: '/tools/subnet', branch_id: 1 },
  { id: 211, name: 'Engineering Unit Converter', description: 'Convert force, pressure, torque, power and speed units.', category: 'Mechanical', route: '/tools/mechanical-units', branch_id: 2 },
  { id: 212, name: 'Area & Volume Calculator', description: 'Calculate common construction areas and volumes.', category: 'Civil', route: '/tools/area-volume', branch_id: 5 },
  { id: 213, name: 'Solution Dilution Calculator', description: 'Practice concentration and dilution calculations with C1V1 = C2V2.', category: 'Laboratory', route: '/tools/mlt-dilution', branch_id: 6 }
]

export const demoAnnouncements = [
  { id: 301, title: 'Semester practical allotments released', message: 'Practical groups for OS and DBMS labs are now available in the dashboard.', created_at: '2026-09-25T11:20:00Z', target_branch_id: 1, target_branch: 'Computer Science' },
  { id: 302, title: 'SkillSwap mentor hours', message: 'Students can book weekend mentor sessions for Python and AutoCAD.', created_at: '2026-09-20T09:00:00Z', target_branch_id: null, target_branch: 'All students' },
  { id: 303, title: 'BookShare drive', message: 'Donate old books for first-year students before the term-end library clearance.', created_at: '2026-09-18T14:00:00Z', target_branch_id: 5, target_branch: 'Civil' }
]

export const demoNotes = [
  { id: 401, title: 'OS CPU Scheduling Notes', description: 'Short notes covering FCFS, SJF, Round Robin and priority scheduling.', file_url: '', file_name: 'os-scheduling.pdf', created_at: '2026-09-23T10:30:00Z', subject: 'Operating System', branch: 'Computer Science', subject_id: 101 },
  { id: 402, title: 'DBMS Normalization Sheet', description: 'One-page summary of functional dependency and normalization forms.', file_url: '', file_name: 'dbms-normalization.pdf', created_at: '2026-09-21T13:10:00Z', subject: 'DBMS', branch: 'Computer Science', subject_id: 102 },
  { id: 403, title: 'Electrical Circuit Fundamentals', description: 'Basic problems on KCL, KVL, series and parallel networks.', file_url: '', file_name: 'circuits-fundamentals.pdf', created_at: '2026-09-19T09:00:00Z', subject: 'Electrical Circuits', branch: 'Electrical', subject_id: 105 }
]

export const demoBooks = [
  { id: 501, title: 'Database System Concepts', author: 'Korth', subject: 'DBMS', action: 'borrow', location: 'Library counter', available_until: '2026-10-12', status: 'available', owner_name: 'Aarav', branch_name: 'Computer Science', branch_id: 1, owner_id: 10 },
  { id: 502, title: 'Thermodynamics for Engineers', author: 'Cengel', subject: 'Thermodynamics', action: 'exchange', location: 'Mechanical block', available_until: '2026-10-14', status: 'available', owner_name: 'Sonia', branch_name: 'Mechanical', branch_id: 2, owner_id: 11 },
  { id: 503, title: 'Industrial Electronics Handbook', author: 'Miller', subject: 'Electronics', action: 'donate', location: 'Workshop shelf', available_until: null, status: 'available', owner_name: 'Rahul', branch_name: 'Electronics', branch_id: 4, owner_id: 12 }
]

export const demoSkills = [
  { id: 601, skill_name: 'Python', type: 'teach', level: 'advanced', name: 'Ishita', branch: 'Computer Science', branch_id: 1, user_id: 20 },
  { id: 602, skill_name: 'AutoCAD', type: 'teach', level: 'intermediate', name: 'Harsh', branch: 'Mechanical', branch_id: 2, user_id: 21 },
  { id: 603, skill_name: 'Embedded C', type: 'learn', level: 'beginner', name: 'Riya', branch: 'Electronics', branch_id: 4, user_id: 22 }
]

export const demoUsers = [
  { id: 1, name: 'Campus Admin', email: 'admin@campushub.local', password_hash: 'demo-admin', role: 'admin', branch_id: 1, semester: null, bio: 'CampusHub platform administrator', branch_name: 'Computer Science' },
  { id: 2, name: 'Aarav Sharma', email: 'aarav@student.edu', password_hash: 'demo-user', role: 'student', branch_id: 1, semester: 5, bio: 'CSE student', branch_name: 'Computer Science' },
  { id: 10, name: 'Aarav', email: 'aarav.book@example.com', password_hash: '', role: 'student', branch_id: 1, semester: 6, bio: 'Book owner', branch_name: 'Computer Science' },
  { id: 11, name: 'Sonia', email: 'sonia.book@example.com', password_hash: '', role: 'student', branch_id: 2, semester: 4, bio: 'Mechanical student', branch_name: 'Mechanical' },
  { id: 12, name: 'Rahul', email: 'rahul.book@example.com', password_hash: '', role: 'student', branch_id: 4, semester: 5, bio: 'Electronics student', branch_name: 'Electronics' },
  { id: 20, name: 'Ishita', email: 'ishita.skill@example.com', password_hash: '', role: 'student', branch_id: 1, semester: 6, bio: 'Python mentor', branch_name: 'Computer Science' },
  { id: 21, name: 'Harsh', email: 'harsh.skill@example.com', password_hash: '', role: 'student', branch_id: 2, semester: 5, bio: 'AutoCAD tutor', branch_name: 'Mechanical' },
  { id: 22, name: 'Riya', email: 'riya.skill@example.com', password_hash: '', role: 'student', branch_id: 4, semester: 3, bio: 'Interested in IoT', branch_name: 'Electronics' }
]

export const defaultDemoState = {
  branches: demoBranches,
  subjects: demoSubjects,
  tools: demoTools,
  notes: demoNotes,
  books: demoBooks,
  skills: demoSkills,
  announcements: demoAnnouncements,
  users: demoUsers,
  bookRequests: [],
  skillRequests: []
}
