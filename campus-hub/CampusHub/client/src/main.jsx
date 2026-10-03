import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, NavLink, Navigate, useNavigate } from 'react-router-dom'
import { api, clearSession, getUser, setSession } from './lib/api'
import './styles/global.css'

const branches = [
  { code: 'CSE', title: 'Computer Science', description: 'Programming, databases, operating systems and project tools.' },
  { code: 'ME', title: 'Mechanical', description: 'Design, mechanics, manufacturing and engineering practice.' },
  { code: 'EE', title: 'Electrical', description: 'Circuits, machines, power systems and measurements.' },
  { code: 'ECE', title: 'Electronics', description: 'Devices, digital systems, embedded design and PCB practice.' },
  { code: 'CE', title: 'Civil', description: 'Surveying, construction, structures and estimation.' },
  { code: 'MLT', title: 'Medical Lab Technology', description: 'Lab science, instruments, procedures and exam preparation.' }
]

function App() {
  const [user, setUser] = useState(getUser())
  const [mobileOpen, setMobileOpen] = useState(false)
  const logout = () => { clearSession(); setUser(null); location.href = '/' }
  return <div className="app-shell">
    <header className="topbar">
      <Link className="brand" to="/" onClick={() => setMobileOpen(false)}><span className="brand-mark">CH</span><div><strong>CampusHub</strong><span>Your campus, in one place.</span></div></Link>
      <button className="menu-btn" onClick={() => setMobileOpen(v => !v)} aria-label={mobileOpen ? 'Close menu' : 'Open menu'}>{mobileOpen ? 'Close' : 'Menu'}</button>
      <nav className={mobileOpen ? 'nav open' : 'nav'}>
        <NavLink to="/branchhub" onClick={() => setMobileOpen(false)}>BranchHub</NavLink>
        <NavLink to="/bookshare" onClick={() => setMobileOpen(false)}>BookShare</NavLink>
        <NavLink to="/skillswap" onClick={() => setMobileOpen(false)}>SkillSwap</NavLink>
        {user?.role && ['admin','super_admin','teacher','moderator'].includes(user.role) && <NavLink to="/admin" onClick={() => setMobileOpen(false)}>Admin</NavLink>}
        {user ? <button className="nav-btn" onClick={logout}>Log out</button> : <NavLink to="/login" onClick={() => setMobileOpen(false)}>Log in</NavLink>}
      </nav>
    </header>
    <main><Routes>
      <Route path="/" element={<Home user={user}/>}/>
      <Route path="/login" element={<Login onLogin={u => setUser(u)}/>}/>
      <Route path="/register" element={<Register onLogin={u => setUser(u)}/>}/>
      <Route path="/branchhub" element={<BranchHub user={user}/>}/>
      <Route path="/bookshare" element={<BookShare user={user}/>}/>
      <Route path="/skillswap" element={<SkillSwap user={user}/>}/>
      <Route path="/admin" element={<AdminPanel user={user}/>}/>
      <Route path="/tools/:tool" element={<ToolPage/>}/>
      <Route path="*" element={<Navigate to="/" replace/>}/>
    </Routes></main>
    <footer>CampusHub • Open-source student ecosystem • Built for campus use</footer>
  </div>
}

function Home({ user }) {
  const [announcements, setAnnouncements] = useState([])
  useEffect(() => { api('/announcements').then(d => setAnnouncements(d.announcements)).catch(() => {}) }, [])
  const modules = [
    { number: '01', title: 'BranchHub', text: 'Find your subjects, notes, practice material and tools.', href: '/branchhub', detail: 'LEARN' },
    { number: '02', title: 'BookShare', text: 'Put useful books back into circulation across campus.', href: '/bookshare', detail: 'EXCHANGE' },
    { number: '03', title: 'SkillSwap', text: 'Trade knowledge with people who can teach what you need.', href: '/skillswap', detail: 'CONNECT' }
  ]
  return <div>
    <section className="home-intro">
      <div className="container">
        <div className="hero">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-mark"></span> MADE FOR CAMPUS</div>
            <h1>Good things<br/>happen <em>between classes.</em></h1>
            <p>Find the notes your class shared, borrow a book from another student, or get help learning something new.</p>
            <div className="hero-actions"><Link className="btn primary" to={user ? '/branchhub' : '/register'}>{user ? 'Open BranchHub' : 'Join your campus'}</Link><Link className="btn ghost" to="/bookshare">See shared books</Link></div>
            <div className="hero-meta"><span>{user?.branch_name || 'For every branch'}</span><span>Student-led resources</span><span>Made to be useful</span></div>
          </div>
          <aside className="hero-card">
            <div className="hero-card-head"><span>A GOOD PLACE TO START</span><span className="status-label">{user?.branch_name || 'CAMPUS'}</span></div>
            <h2>{user ? `Good to see you, ${user.name.split(' ')[0]}.` : 'What are you here for?'}</h2>
            <p>{user?.branch_name ? `A few useful things from ${user.branch_name}.` : 'Choose what you need. You can look around first.'}</p>
            <div className="dashboard-list">
              <Link to="/branchhub"><span className="dashboard-index">01</span><span><strong>Study hub</strong><small>Notes, subjects and practice</small></span><span className="text-arrow">↗</span></Link>
              <Link to="/bookshare"><span className="dashboard-index">02</span><span><strong>Book exchange</strong><small>Borrow, lend, pass it on</small></span><span className="text-arrow">↗</span></Link>
              <Link to="/skillswap"><span className="dashboard-index">03</span><span><strong>Peer skills</strong><small>Learn together, across branches</small></span><span className="text-arrow">↗</span></Link>
            </div>
            <div className="hero-card-foot"><span>LEARN</span><span>SHARE</span><span>BUILD</span><span>GROW</span></div>
          </aside>
        </div>
      </div>
    </section>
    <section className="container section module-section">
      <div className="section-head"><div><span className="eyebrow">START HERE</span><h2>What do you need today?</h2></div><p className="section-intro">Pick a section and take it from there.</p></div>
      <div className="module-list">{modules.map(module => <Link to={module.href} className="module-row" key={module.number}><span className="module-number">{module.number}</span><span className="module-main"><strong>{module.title}</strong><small>{module.text}</small></span><span className="module-detail">{module.detail}</span><span className="module-arrow">↗</span></Link>)}</div>
    </section>
    <section className="branch-section">
      <div className="container section">
        <div className="section-head"><div><span className="eyebrow">THE ACADEMIC SIDE</span><h2>Find your branch.</h2></div><Link className="text-link" to="/branchhub">Browse subjects <span>↗</span></Link></div>
        <div className="branch-grid">{branches.map((branch, index) => <Link className="branch-card" key={branch.code} to={`/branchhub?branch=${branch.code}`}><span className="branch-index">{String(index + 1).padStart(2, '0')}</span><div><span className="branch-code">{branch.code}</span><strong>{branch.title}</strong><p>{branch.description}</p></div><span className="branch-arrow">↗</span></Link>)}</div>
      </div>
    </section>
    <section className="container section announcement-section">
      <div className="section-head"><div><span className="eyebrow">PINNED FOR EVERYONE</span><h2>Campus notices.</h2></div></div>
      <div className="announcement-list">{announcements.length ? announcements.map(a => <article className="announcement" key={a.id}><div><span className="tag">{a.target_branch || 'ALL STUDENTS'}</span><h3>{a.title}</h3><p>{a.message}</p></div><time>{new Date(a.created_at).toLocaleDateString()}</time></article>) : <Empty text="No announcements yet. Admins can publish campus updates here."/>}</div>
    </section>
  </div>
}

function Empty({text}) { return <div className="empty">{text}</div> }
function PageHeader({eyebrow,title,text}) { return <section className="page-header container"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{text}</p></section> }

function Login({onLogin}) {
  const nav = useNavigate(); const [form,setForm]=useState({email:'',password:''}); const [error,setError]=useState(''); const [loading,setLoading]=useState(false)
  const submit = async e => { e.preventDefault(); setError(''); setLoading(true); try { const d=await api('/auth/login',{method:'POST',body:JSON.stringify(form)}); setSession(d); onLogin(d.user); nav(d.user.role==='admin'||d.user.role==='super_admin'||d.user.role==='teacher'||d.user.role==='moderator'?'/admin':'/branchhub') } catch(err){ setError(err.message) } finally {setLoading(false)} }
  return <div className="auth-wrap"><div className="auth-card"><span className="eyebrow">WELCOME BACK</span><h1>Login to CampusHub</h1><p>Use your student or authorized staff account.</p>{error && <div className="error">{error}</div>}<form onSubmit={submit} className="form"><label>Email<input type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} required/></label><label>Password<input type="password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} required/></label><button className="btn primary full" disabled={loading}>{loading?'Signing in...':'Login'}</button></form><p className="muted">New student? <Link to="/register">Create an account</Link></p></div></div>
}

function Register({onLogin}) {
  const nav = useNavigate(); const [branches,setBranches]=useState([]); const [form,setForm]=useState({name:'',email:'',password:'',branchId:'',semester:''}); const [error,setError]=useState(''); const [loading,setLoading]=useState(false)
  useEffect(()=>{api('/branches').then(d=>setBranches(d.branches)).catch(()=>{})},[])
  const submit=async e=>{e.preventDefault();setError('');setLoading(true);try{const d=await api('/auth/register',{method:'POST',body:JSON.stringify(form)});setSession(d);onLogin(d.user);nav('/branchhub')}catch(err){setError(err.message)}finally{setLoading(false)}}
  return <div className="auth-wrap"><div className="auth-card wide"><span className="eyebrow">JOIN THE CAMPUS</span><h1>Create your student account</h1><p>Pick your branch now; you can personalize resources later.</p>{error&&<div className="error">{error}</div>}<form onSubmit={submit} className="form two"><label>Full Name<input value={form.name} onChange={e=>setForm({...form,name:e.target.value})} required/></label><label>Email<input type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} required/></label><label>Password<input type="password" minLength="6" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} required/></label><label>Semester<input type="number" min="1" max="12" value={form.semester} onChange={e=>setForm({...form,semester:e.target.value})}/></label><label className="span-2">Branch<select value={form.branchId} onChange={e=>setForm({...form,branchId:e.target.value})}><option value="">Select branch</option>{branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label><button className="btn primary full span-2" disabled={loading}>{loading?'Creating...':'Create account'}</button></form><p className="muted">Already have an account? <Link to="/login">Login</Link></p></div></div>
}

function BranchHub({user}) {
  const [branches,setBranches]=useState([]),[selected,setSelected]=useState(''),[subjects,setSubjects]=useState([]),[notes,setNotes]=useState([]),[tools,setTools]=useState([]),[q,setQ]=useState('')
  useEffect(()=>{api('/branches').then(d=>{setBranches(d.branches); const p=new URLSearchParams(location.search).get('branch'); const found=d.branches.find(x=>x.code===p)||d.branches.find(x=>x.id===user?.branch_id); setSelected(found?.id||'')}).catch(()=>{})},[user?.branch_id])
  useEffect(()=>{if(!selected){setSubjects([]);setNotes([]);return} Promise.all([api(`/subjects?branchId=${selected}`),api(`/notes?branchId=${selected}`),api(`/tools?branchId=${selected}`)]).then(([s,n,t])=>{setSubjects(s.subjects);setNotes(n.notes);setTools(t.tools)}).catch(()=>{})},[selected])
  const filteredTools=tools.filter(t=>!q||`${t.name} ${t.description}`.toLowerCase().includes(q.toLowerCase()))
  const branch=branches.find(b=>b.id===selected)
  return <div><PageHeader eyebrow="BRANCHHUB" title="Your branch, one workspace." text="Every subject follows the same pattern: notes, practicals, viva, MCQs, previous questions and useful tools."/><section className="container section"><div className="toolbar"><div className="select-wrap"><span>Branch</span><select value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Select a branch</option>{branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></div><label className="search-box"><span className="search-label">SEARCH</span><input placeholder="Subjects or tools..." value={q} onChange={e=>setQ(e.target.value)}/></label></div>{branch&&<div className="branch-hero"><span className="branch-code-large">{branch.code}</span><div><span className="eyebrow">YOUR BRANCH</span><h2>{branch.name}</h2><p>Pick a subject and explore the resources available today.</p></div></div>}<div className="subject-grid">{subjects.filter(s=>!q||s.name.toLowerCase().includes(q.toLowerCase())).map((s,index)=><div className="subject-card" key={s.id}><div className="subject-top"><span className="subject-index">{String(index+1).padStart(2,'0')}</span><small>{branch?.code}</small></div><h3>{s.name}</h3><div className="subject-links"><a href="#notes">Notes</a><a href="#practicals">Practicals</a><a href="#viva">Viva</a><a href="#mcqs">MCQs</a></div></div>)}</div></section><section id="notes" className="container section"><div className="section-head"><div><span className="eyebrow">RESOURCES</span><h2>Latest notes</h2></div></div>{notes.length?<div className="resource-list">{notes.map(n=><article className="resource" key={n.id}><div><span className="tag">{n.subject}</span><h3>{n.title}</h3><p>{n.description}</p></div>{n.file_url?<a className="btn small" href={`${(import.meta.env.VITE_API_URL||'http://localhost:5000/api').replace('/api','')}${n.file_url}`} target="_blank">Open file</a>:<span className="muted">No file</span>}</article>)}</div>:<Empty text="No notes added yet. Admins can upload PDFs from the admin panel."/>}</section><section className="container section"><div className="section-head"><div><span className="eyebrow">MINI TOOLS LAB</span><h2>Tools for {branch?.code||'your branch'}</h2></div></div><div className="tool-grid">{filteredTools.map(t=><Link to={t.route} className="tool-card" key={t.id}><span className="tool-category">{t.category}</span><div><strong>{t.name}</strong><p>{t.description}</p><small>Open tool ↗</small></div></Link>)}{!filteredTools.length&&<Empty text="No matching tools yet."/>}</div></section></div>
}

function BookShare({user}) {
  const [books,setBooks]=useState([]),[q,setQ]=useState(''),[form,setForm]=useState({title:'',author:'',subject:'',location:'',action:'borrow'}),[msg,setMsg]=useState('')
  const load=()=>api(`/books${q?`?q=${encodeURIComponent(q)}`:''}`).then(d=>setBooks(d.books)).catch(()=>{})
  useEffect(load,[])
  const add=async e=>{e.preventDefault();if(!user){setMsg('Login required to list a book.');return}try{await api('/user/books',{method:'POST',body:JSON.stringify(form)});setForm({title:'',author:'',subject:'',location:'',action:'borrow'});setMsg('Book listed.');load()}catch(err){setMsg(err.message)}}
  return <div><PageHeader eyebrow="BOOKSHARE" title="Keep useful resources moving." text="Borrow, lend, exchange or donate academic books and equipment inside your campus."/><section className="container section split"><div className="panel"><span className="eyebrow">FIND A BOOK</span><label className="search-box big"><span className="search-label">SEARCH</span><input placeholder="Title, author or subject..." value={q} onChange={e=>{setQ(e.target.value);load()}}/></label><div className="resource-list">{books.map(b=><article className="resource" key={b.id}><div><span className="tag">{b.branch_name||'General'} • {b.action}</span><h3>{b.title}</h3><p>{b.author||'Unknown author'} · {b.subject||'Academic resource'}</p><small>Owner: {b.owner_name} · {b.location||'Campus'} </small></div><button className="btn small" onClick={async()=>{if(!user){alert('Login to request a book.');return}try{await api('/user/book-requests',{method:'POST',body:JSON.stringify({bookId:b.id})});alert('Request sent.')}catch(err){alert(err.message)}}}>Request</button></article>)}{!books.length&&<Empty text="No books found yet."/>}</div></div><div className="panel"><span className="eyebrow">LIST RESOURCE</span><h2>Share a book</h2>{msg&&<div className="notice">{msg}</div>}<form className="form" onSubmit={add}><label>Title<input value={form.title} onChange={e=>setForm({...form,title:e.target.value})} required/></label><label>Author<input value={form.author} onChange={e=>setForm({...form,author:e.target.value})}/></label><label>Subject<input value={form.subject} onChange={e=>setForm({...form,subject:e.target.value})}/></label><label>Location<input value={form.location} onChange={e=>setForm({...form,location:e.target.value})} placeholder="Library / Block A"/></label><label>Action<select value={form.action} onChange={e=>setForm({...form,action:e.target.value})}><option value="borrow">Borrow</option><option value="exchange">Exchange</option><option value="donate">Donate</option></select></label><button className="btn primary full">List resource</button></form></div></section></div>
}

function SkillSwap({user}) {
  const [skills,setSkills]=useState([]),[q,setQ]=useState(''),[form,setForm]=useState({skillName:'',type:'teach',level:'beginner'}),[msg,setMsg]=useState('')
  const load=()=>api(`/skills${q?`?q=${encodeURIComponent(q)}`:''}`).then(d=>setSkills(d.skills)).catch(()=>{})
  useEffect(load,[])
  const add=async e=>{e.preventDefault();if(!user){setMsg('Login required to add a skill.');return}try{await api('/user/skills',{method:'POST',body:JSON.stringify(form)});setForm({skillName:'',type:'teach',level:'beginner'});setMsg('Skill added.');load()}catch(err){setMsg(err.message)}}
  return <div><PageHeader eyebrow="SKILLSWAP" title="Teach one skill. Learn another." text="Build meaningful peer connections, including cross-branch exchanges."/><section className="container section split"><div className="panel"><span className="eyebrow">DISCOVER</span><label className="search-box big"><span className="search-label">SEARCH</span><input placeholder="Python, AutoCAD, SQL..." value={q} onChange={e=>{setQ(e.target.value);load()}}/></label><div className="skill-grid">{skills.map(s=><article className="skill-card" key={s.id}><div><span className="tag">{s.type.toUpperCase()}</span><h3>{s.skill_name}</h3><p>{s.name} · {s.branch||'General'}</p><small>{s.level}</small></div><button className="btn small">Connect</button></article>)}{!skills.length&&<Empty text="No skills listed yet."/>}</div></div><div className="panel"><span className="eyebrow">MY SKILLS</span><h2>Publish a skill</h2>{msg&&<div className="notice">{msg}</div>}<form className="form" onSubmit={add}><label>Skill<input value={form.skillName} onChange={e=>setForm({...form,skillName:e.target.value})} placeholder="Python" required/></label><label>I want to<select value={form.type} onChange={e=>setForm({...form,type:e.target.value})}><option value="teach">Teach it</option><option value="learn">Learn it</option></select></label><label>Level<select value={form.level} onChange={e=>setForm({...form,level:e.target.value})}><option>beginner</option><option>intermediate</option><option>advanced</option></select></label><button className="btn primary full">Publish</button></form></div></section></div>
}

function AdminPanel({user}) {
  if (!user || !['admin','super_admin','teacher','moderator'].includes(user.role)) return <Navigate to="/login" replace/>
  const [stats,setStats]=useState({}),[branches,setBranches]=useState([]),[subjects,setSubjects]=useState([]),[note,setNote]=useState({title:'',description:'',subjectId:'',file:null}),[announcement,setAnnouncement]=useState({title:'',message:'',targetBranchId:''}),[msg,setMsg]=useState('')
  useEffect(()=>{api('/admin/stats').then(setStats).catch(()=>{});api('/branches').then(d=>setBranches(d.branches)).catch(()=>{})},[])
  useEffect(()=>{api('/subjects').then(d=>setSubjects(d.subjects)).catch(()=>{})},[])
  const upload=async e=>{e.preventDefault();try{const fd=new FormData();fd.append('title',note.title);fd.append('description',note.description);fd.append('subjectId',note.subjectId);if(note.file)fd.append('file',note.file);await api('/admin/notes',{method:'POST',body:fd});setMsg('Note uploaded successfully.');setNote({title:'',description:'',subjectId:'',file:null})}catch(err){setMsg(err.message)}}
  const publish=async e=>{e.preventDefault();try{await api('/admin/announcements',{method:'POST',body:JSON.stringify(announcement)});setMsg('Announcement published.');setAnnouncement({title:'',message:'',targetBranchId:''})}catch(err){setMsg(err.message)}}
  return <div><PageHeader eyebrow="ADMIN CONTROL CENTER" title="Manage the campus knowledge base." text="Upload notes, publish announcements and keep the platform fresh. The backend also enforces role-based access."/><section className="container section"><div className="stats">{[['Students',stats.users||0],['Notes',stats.notes||0],['Books',stats.books||0],['Skills',stats.skills||0],['Announcements',stats.announcements||0]].map(([label,val])=><div className="stat" key={label}><strong>{val}</strong><small>{label}</small></div>)}</div>{msg&&<div className="notice">{msg}</div>}<div className="admin-grid"><div className="panel"><span className="eyebrow">CONTENT</span><h2>Upload a note</h2><form className="form" onSubmit={upload}><label>Title<input value={note.title} onChange={e=>setNote({...note,title:e.target.value})} required/></label><label>Description<textarea value={note.description} onChange={e=>setNote({...note,description:e.target.value})}/></label><label>Subject<select value={note.subjectId} onChange={e=>setNote({...note,subjectId:e.target.value})} required><option value="">Choose subject</option>{subjects.map(s=><option key={s.id} value={s.id}>{s.code} · {s.name}</option>)}</select></label><label>File (PDF/PNG/JPG, max 10MB)<input type="file" accept="application/pdf,image/png,image/jpeg" onChange={e=>setNote({...note,file:e.target.files?.[0]||null})}/></label><button className="btn primary full">Upload note</button></form></div><div className="panel"><span className="eyebrow">ANNOUNCEMENT</span><h2>Publish an update</h2><form className="form" onSubmit={publish}><label>Title<input value={announcement.title} onChange={e=>setAnnouncement({...announcement,title:e.target.value})} required/></label><label>Message<textarea value={announcement.message} onChange={e=>setAnnouncement({...announcement,message:e.target.value})} required/></label><label>Target<select value={announcement.targetBranchId} onChange={e=>setAnnouncement({...announcement,targetBranchId:e.target.value})}><option value="">All students</option>{branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label><button className="btn primary full">Publish announcement</button></form></div></div></section></div>
}

function ToolPage(){
  const {tool}=requireParams();
  const configs={
    percentage:{title:'Percentage Calculator'},cgpa:{title:'CGPA Calculator'},units:{title:'Unit Converter'},python:{title:'Python Playground'},sql:{title:'SQL Query Practice'},linux:{title:'Linux Command Helper'},subnet:{title:'IP / Subnet Calculator'},'ohms-law':{title:"Ohm's Law Calculator"},power:{title:'Power Calculator'},'logic-gates':{title:'Logic Gate Helper'},'mechanical-units':{title:'Mechanical Unit Converter'},'area-volume':{title:'Area & Volume Calculator'}
  }
  const meta=configs[tool]||{title:'Campus Tool'}
  return <div><PageHeader eyebrow="MINI TOOLS LAB" title={meta.title} text="A lightweight tool starter. More branch-specific calculators and simulators can be plugged into this route structure later."/><div className="container section"><div className="tool-workspace">{tool==='percentage'?<PercentageTool/>:tool==='cgpa'?<CgpaTool/>:tool==='ohms-law'?<OhmTool/>:tool==='power'?<PowerTool/>:tool==='area-volume'?<AreaTool/>:tool==='logic-gates'?<LogicTool/>:tool==='linux'?<LinuxTool/>:<ComingTool title={meta.title}/>}</div></div></div>
}
function requireParams(){ const p=location.pathname.split('/').filter(Boolean); return {tool:p[1]||''} }
function PercentageTool(){const [a,setA]=useState(''),[b,setB]=useState('');const r=a&&b?((Number(a)/Number(b))*100).toFixed(2):'—';return <SimpleCalc title="What percent is A of B?" fields={[['A',a,setA],['B',b,setB]]} result={`${r}%`}/>}
function CgpaTool(){const [vals,setVals]=useState('8,7.5,9,8.2');const arr=vals.split(',').map(Number).filter(n=>Number.isFinite(n));const r=arr.length?(arr.reduce((a,b)=>a+b,0)/arr.length).toFixed(2):'—';return <div className="simple-tool"><h2>CGPA</h2><p>Enter semester/subject GPAs separated by commas.</p><input value={vals} onChange={e=>setVals(e.target.value)}/><div className="result"><span>Average</span><strong>{r}</strong></div></div>}
function OhmTool(){const [v,setV]=useState(''),[i,setI]=useState(''),[r,setR]=useState('');const res=v&&r?`I = ${(Number(v)/Number(r)).toFixed(3)} A`:i&&r?`V = ${(Number(i)*Number(r)).toFixed(3)} V`:v&&i?`R = ${(Number(v)/Number(i)).toFixed(3)} Ω`:'Enter any two values';return <div className="simple-tool"><h2>Ohm's Law</h2><div className="three-inputs"><label>Voltage (V)<input value={v} onChange={e=>setV(e.target.value)}/></label><label>Current (A)<input value={i} onChange={e=>setI(e.target.value)}/></label><label>Resistance (Ω)<input value={r} onChange={e=>setR(e.target.value)}/></label></div><div className="result"><span>Result</span><strong>{res}</strong></div></div>}
function PowerTool(){const [v,setV]=useState(''),[i,setI]=useState('');const p=v&&i?(Number(v)*Number(i)).toFixed(2):'—';return <SimpleCalc title="DC power: P = V × I" fields={[['Voltage (V)',v,setV],['Current (A)',i,setI]]} result={`${p} W`}/>}
function AreaTool(){const [l,setL]=useState(''),[w,setW]=useState('');const a=l&&w?(Number(l)*Number(w)).toFixed(2):'—';return <SimpleCalc title="Rectangle area" fields={[['Length',l,setL],['Width',w,setW]]} result={`${a} square units`}/>}
function LogicTool(){const [a,setA]=useState(false),[b,setB]=useState(false);return <div className="simple-tool"><h2>Logic Gates</h2><div className="logic-inputs"><label><input type="checkbox" checked={a} onChange={e=>setA(e.target.checked)}/> A</label><label><input type="checkbox" checked={b} onChange={e=>setB(e.target.checked)}/> B</label></div><div className="logic-results"><span>AND: {a&&b?1:0}</span><span>OR: {a||b?1:0}</span><span>NAND: {a&&b?0:1}</span><span>XOR: {a!==b?1:0}</span><span>NOT A: {a?0:1}</span></div></div>}
function LinuxTool(){return <div className="simple-tool"><h2>Linux Command Helper</h2><div className="cmd-grid">{[['ls','List files'],['cd','Change directory'],['pwd','Show current directory'],['mkdir','Create directory'],['cp','Copy files'],['mv','Move/rename files'],['rm','Remove files'],['grep','Search text']].map(([c,d])=><div className="cmd" key={c}><code>{c}</code><span>{d}</span></div>)}</div></div>}
function ComingTool({title}){return <div className="simple-tool"><h2>{title}</h2><p>This route is wired into CampusHub and ready for a richer calculator/simulator. The current starter keeps the core platform working without paid APIs.</p><div className="notice">Next development step: add the branch-specific algorithm here and connect it from BranchHub.</div></div>}
function SimpleCalc({title,fields,result}){return <div className="simple-tool"><h2>{title}</h2><div className="three-inputs">{fields.map(([label,v,setV])=><label key={label}>{label}<input value={v} onChange={e=>setV(e.target.value)} inputMode="decimal"/></label>)}</div><div className="result"><span>Result</span><strong>{result}</strong></div></div>}

createRoot(document.getElementById('root')).render(<BrowserRouter><App/></BrowserRouter>)
