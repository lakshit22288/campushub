import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'
import bcrypt from 'bcryptjs'
import dotenv from 'dotenv'

dotenv.config({ path: path.resolve(process.cwd(), '.env') })
const { pool } = await import('../src/db/pool.js')

const branches = [
  { name: 'Computer Science / IT', code: 'CSE', icon: '💻', subjects: ['C Programming','C++ Programming','Java','Python','PHP','HTML/CSS/JavaScript','Web Development','DBMS','SQL','Data Structures & Algorithms','Computer Networks','Operating Systems','Linux','Cloud Computing','Computer Organization & Architecture','Digital Electronics','Software Engineering','Computer Graphics','Microprocessor/Microcontroller','Cyber Security','IoT','Mobile Application Development','Artificial Intelligence / ML Basics','Git & GitHub','Programming Practice'] },
  { name: 'Mechanical Engineering', code: 'ME', icon: '⚙️', subjects: ['Engineering Drawing','AutoCAD','CAD/CAM','Workshop Technology','Manufacturing Processes','Thermodynamics','Fluid Mechanics','Strength of Materials','Machine Design','Theory of Machines','Metrology','Production Engineering','Material Science','Mechanical Measurements','Engineering Mechanics','CNC Basics'] },
  { name: 'Electrical Engineering', code: 'EE', icon: '⚡', subjects: ['Basic Electrical Engineering','Electrical Circuits','Ohm\'s Law','Kirchhoff\'s Laws','AC/DC','Network Theorems','Transformers','Electrical Machines','Motors','Generators','Power Systems','Measurements & Instruments','Wiring','Electrical Safety'] },
  { name: 'Electronics Engineering', code: 'ECE', icon: '📡', subjects: ['Electronic Devices','Diodes','Transistors','Rectifiers','Amplifiers','Oscillators','Digital Electronics','Logic Gates','Boolean Algebra','Flip-Flops','Counters','Registers','Microprocessors','Microcontrollers','Communication Systems','PCB','Embedded Systems','Sensors','IoT'] },
  { name: 'Civil Engineering', code: 'CE', icon: '🏗️', subjects: ['Engineering Drawing','AutoCAD','Surveying','Building Materials','Building Construction','Concrete Technology','Strength of Materials','Structural Engineering','Soil Mechanics','Hydraulics','Environmental Engineering','Transportation Engineering','Estimation & Costing','Quantity Surveying','RCC Basics'] },
  { name: 'Medical Laboratory Technology', code: 'MLT', icon: '🧪', subjects: ['Anatomy & Physiology','Biochemistry','Microbiology','Hematology','Pathology','Clinical Biochemistry','Immunology','Histopathology','Blood Banking','Laboratory Instruments','Microscope Guide','Lab Safety','Specimen Collection','Laboratory Procedures','Medical Terminology'] }
]

const tools = [
  ['General','Percentage Calculator','Percentage, marks and increase/decrease calculations.','calculator','/tools/percentage','🧮'],
  ['General','CGPA Calculator','Calculate CGPA from semester or subject scores.','calculator','/tools/cgpa','🎓'],
  ['General','Unit Converter','Convert common engineering and study units.','converter','/tools/units','📏'],
  ['CSE','Python Playground','Run or practice simple Python snippets.','coding','/tools/python','🐍'],
  ['CSE','SQL Query Practice','Write and format SQL queries in a practice workspace.','database','/tools/sql','🗄️'],
  ['CSE','Linux Command Helper','Search common Linux commands and examples.','reference','/tools/linux','🐧'],
  ['CSE','IP/Subnet Calculator','Practice IPv4 network calculations.','networking','/tools/subnet','🌐'],
  ['EE','Ohm\'s Law Calculator','Calculate voltage, current, resistance and power.','electrical','/tools/ohms-law','⚡'],
  ['EE','Power Calculator','Calculate DC/AC power using common formulas.','electrical','/tools/power','🔌'],
  ['ECE','Logic Gate Helper','Practice AND, OR, NOT and basic Boolean operations.','electronics','/tools/logic-gates','📡'],
  ['ME','Engineering Unit Converter','Common force, pressure, torque and power conversions.','mechanical','/tools/mechanical-units','⚙️'],
  ['CE','Area & Volume Calculator','Common construction geometry calculations.','civil','/tools/area-volume','🏗️']
]

try {
  const schemaPath = new URL('../server/src/db/schema.sql', import.meta.url)
  const schema = await fs.readFile(schemaPath, 'utf8')
  await pool.query(schema)

  const branchIds = new Map()
  for (const b of branches) {
    const result = await pool.query(
      `INSERT INTO branches(name,code,icon) VALUES($1,$2,$3)
       ON CONFLICT(code) DO UPDATE SET name=EXCLUDED.name,icon=EXCLUDED.icon
       RETURNING id`, [b.name,b.code,b.icon]
    )
    branchIds.set(b.code, result.rows[0].id)
    for (const subject of b.subjects) {
      const slug = subject.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')
      await pool.query(`INSERT INTO subjects(branch_id,name,slug) VALUES($1,$2,$3) ON CONFLICT(branch_id,slug) DO NOTHING`, [result.rows[0].id, subject, slug])
    }
  }

  for (const [branchCode, name, description, category, route, icon] of tools) {
    const branchId = branchCode === 'General' ? null : branchIds.get(branchCode)
    await pool.query(
      `INSERT INTO tools(branch_id,name,slug,description,category,route,icon)
       VALUES($1,$2,$3,$4,$5,$6,$7)
       ON CONFLICT(slug) DO UPDATE SET name=EXCLUDED.name,description=EXCLUDED.description,category=EXCLUDED.category,route=EXCLUDED.route,icon=EXCLUDED.icon`,
      [branchId,name,name.toLowerCase().replace(/[^a-z0-9]+/g,'-'),description,category,route,icon]
    )
  }

  const adminEmail = process.env.SEED_ADMIN_EMAIL || 'admin@campushub.local'
  const adminPassword = process.env.SEED_ADMIN_PASSWORD || 'ChangeMe123!'
  const hash = await bcrypt.hash(adminPassword, 12)
  await pool.query(
    `INSERT INTO users(name,email,password_hash,role)
     VALUES($1,$2,$3,'super_admin')
     ON CONFLICT(email) DO UPDATE SET role='super_admin'`,
    ['CampusHub Admin',adminEmail,hash]
  )

  const allBranches = [...branchIds.keys()]
  const announcement = await pool.query(`SELECT 1 FROM announcements LIMIT 1`)
  if (!announcement.rowCount) {
    const admin = await pool.query(`SELECT id FROM users WHERE email=$1`, [adminEmail])
    await pool.query(`INSERT INTO announcements(title,message,created_by) VALUES($1,$2,$3)`, [
      'Welcome to CampusHub',
      'CampusHub is ready for students. Explore BranchHub, BookShare and SkillSwap.',
      admin.rows[0].id
    ])
  }

  console.log('Seed complete.')
  console.log(`Admin email: ${adminEmail}`)
  console.log(`Admin password: ${adminPassword}`)
  console.log(`Branches seeded: ${allBranches.join(', ')}`)
} catch (err) {
  console.error('Seed failed:', err)
  process.exitCode = 1
} finally {
  await pool.end()
}
