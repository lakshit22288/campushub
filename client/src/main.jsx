import React, { useCallback, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, NavLink, Navigate, useNavigate } from 'react-router-dom'
import { api, clearSession, getUser, setSession } from './lib/api'
import Compiler from './Compiler'
import ProjectIdeas from './ProjectIdeas'
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
  const updateUser = useCallback(value => setUser(value), [])
  const logout = () => { clearSession(); setUser(null); location.href = '/' }
  return <div className="app-shell">
    <header className="topbar">
      <Link className="brand" to="/" onClick={() => setMobileOpen(false)}><span className="brand-mark">CH</span><div><strong>CampusHub</strong><span>Your campus, in one place.</span></div></Link>
      <button className="menu-btn" onClick={() => setMobileOpen(v => !v)} aria-label={mobileOpen ? 'Close menu' : 'Open menu'}>{mobileOpen ? 'Close' : 'Menu'}</button>
      <nav className={mobileOpen ? 'nav open' : 'nav'}>
        <NavLink to="/branchhub" onClick={() => setMobileOpen(false)}>BranchHub</NavLink>
        <NavLink to="/compiler" onClick={() => setMobileOpen(false)}>Code Lab</NavLink>
        <NavLink to="/project-ideas" onClick={() => setMobileOpen(false)}>Project ideas</NavLink>
        <NavLink to="/bookshare" onClick={() => setMobileOpen(false)}>BookShare</NavLink>
        <NavLink to="/skillswap" onClick={() => setMobileOpen(false)}>SkillSwap</NavLink>
        {user?.role && ['admin','super_admin','teacher','moderator'].includes(user.role) && <NavLink to="/admin" onClick={() => setMobileOpen(false)}>Admin</NavLink>}
        {user ? <button className="nav-btn" onClick={logout}>Log out</button> : <NavLink to="/login" onClick={() => setMobileOpen(false)}>Log in</NavLink>}
      </nav>
    </header>
    <main><Routes>
      <Route path="/" element={<Home user={user}/>}/>
      <Route path="/login" element={<Login onLogin={updateUser}/>}/>
      <Route path="/register" element={<Register onLogin={updateUser}/>}/>
      <Route path="/auth/callback" element={<GoogleAuthCallback onLogin={updateUser}/>}/>
      <Route path="/branchhub" element={<BranchHub user={user}/>}/>
      <Route path="/compiler" element={<CodeLabPage/>}/>
      <Route path="/project-ideas" element={<ProjectIdeasPage/>}/>
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
            <div className="eyebrow"><span className="eyebrow-mark"></span> YOUR CAMPUS, IN MOTION</div>
            <h1>Learn something.<br/><em>Build something.</em></h1>
            <p>Branch tools, a code lab, student-powered skill exchange and the resources that make campus life easier.</p>
            <div className="hero-actions"><Link className="btn primary" to={user ? '/branchhub' : '/register'}>{user ? 'Open your workspace' : 'Get started'}<span className="button-arrow" aria-hidden="true">↗</span></Link><Link className="btn ghost" to="/compiler">Open Code Lab</Link></div>
            <div className="hero-meta"><span>{user?.branch_name || '6 branches'}</span><span>10 compiler languages</span><span>Built for student projects</span></div>
          </div>
          <aside className="hero-card">
            <div className="lab-window">
              <div className="lab-window-top"><span>QUICK START / PYTHON</span><span>READY</span></div>
              <div className="lab-code"><span>01</span><code>skills = ["ideas", "people"]</code><span>02</span><code>print("Let's build.")</code></div>
              <div className="lab-window-output"><span>OUTPUT</span><strong>Let's build.</strong></div>
              <Link to="/compiler" className="lab-window-link">Try it in Code Lab <span aria-hidden="true">↗</span></Link>
            </div>
            <div className="hero-card-caption"><span>{user ? `Welcome back, ${user.name.split(' ')[0]}` : 'One campus. More ways to learn.'}</span><span>{user?.branch_name || 'CAMPUSHUB / 2026'}</span></div>
          </aside>
        </div>
      </div>
    </section>
    <section className="container section module-section">
      <div className="section-head"><div><span className="eyebrow">START HERE</span><h2>What do you need today?</h2></div><p className="section-intro">Pick a section and take it from there.</p></div>
      <div className="module-list">{modules.map(module => <Link to={module.href} className="module-row" key={module.number}><span className="module-number">{module.number}</span><span className="module-main"><strong>{module.title}</strong><small>{module.text}</small></span><span className="module-detail">{module.detail}</span><span className="module-arrow">↗</span></Link>)}</div>
    </section>
    <section className="container section explore-section">
      <div className="section-head"><div><span className="eyebrow">THE BUILDING BLOCKS</span><h2>From first idea to first run.</h2></div><p className="section-intro">Learn it, test it, make it real.</p></div>
      <div className="explore-grid">
        <Link to="/compiler" className="explore-card explore-card-featured"><span className="explore-index">01 / CODE</span><span className="explore-count">10 languages</span><strong>Code Lab</strong><p>Write a program, add input and run it from one focused workspace.</p><span className="explore-link">Open compiler ↗</span></Link>
        <Link to="/project-ideas" className="explore-card"><span className="explore-index">02 / MAKE</span><span className="explore-count">6 branches</span><strong>Project ideas</strong><p>Find a practical starting point matched to your branch and level.</p><span className="explore-link">Get an idea ↗</span></Link>
        <Link to="/branchhub" className="explore-card"><span className="explore-index">03 / LEARN</span><span className="explore-count">Branch-first</span><strong>Interactive tools</strong><p>Calculators, reference sheets and practice for your course.</p><span className="explore-link">Explore tools ↗</span></Link>
        <Link to="/skillswap" className="explore-card"><span className="explore-index">04 / SHARE</span><span className="explore-count">Peer learning</span><strong>SkillSwap</strong><p>Trade time and knowledge with students who know what you want to learn.</p><span className="explore-link">Meet your match ↗</span></Link>
      </div>
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

function CodeLabPage() {
  return <div><PageHeader eyebrow="INTERACTIVE LAB · PROGRAMMING" title="Your next idea starts in code." text="Choose a language, write a program and see what it does. Nothing from your run is saved to your CampusHub profile."/><div className="container section"><Compiler/></div></div>
}

function ProjectIdeasPage() {
  return <div><PageHeader eyebrow="PROJECT STUDIO · BUILT FOR EVERY BRANCH" title="A blank page is the hardest part." text="Choose a branch and a difficulty. Get a project starter with skills, possible features and a realistic scope to shape with your team."/><div className="container section"><ProjectIdeas/></div></div>
}

function GoogleSignInButton({onError}) {
  const [loading,setLoading]=useState(false)
  const start=async()=>{
    setLoading(true)
    onError('')
    try {
      const {signInWithGoogle}=await import('./lib/supabase')
      await signInWithGoogle()
    }
    catch(error) { onError(error.message); setLoading(false) }
  }
  return <button className="btn ghost full" type="button" onClick={start} disabled={loading}>{loading?'Opening Google...':'Continue with Google'}</button>
}

function clearGoogleSessionInBackground(supabaseClient) {
  supabaseClient.auth.signOut()
    .then(({error}) => {
      if (error) console.error('Could not clear the Supabase session after CampusHub sign-in:', error)
    })
    .catch(error => console.error('Could not clear the Supabase session after CampusHub sign-in:', error))
}

function Login({onLogin}) {
  const nav = useNavigate(); const [form,setForm]=useState({email:'',password:''}); const [error,setError]=useState(''); const [loading,setLoading]=useState(false)
  const submit = async e => { e.preventDefault(); setError(''); setLoading(true); try { const d=await api('/auth/login',{method:'POST',body:JSON.stringify(form)}); setSession(d); onLogin(d.user); nav(d.user.role==='admin'||d.user.role==='super_admin'||d.user.role==='teacher'||d.user.role==='moderator'?'/admin':'/branchhub') } catch(err){ setError(err.message) } finally {setLoading(false)} }
  return <div className="auth-wrap"><div className="auth-card"><span className="eyebrow">WELCOME BACK</span><h1>Login to CampusHub</h1><p>Use your student or authorized staff account.</p>{error && <div className="error">{error}</div>}<GoogleSignInButton onError={setError}/><div className="auth-divider">or use email and password</div><form onSubmit={submit} className="form"><label>Email<input type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} required/></label><label>Password<input type="password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} required/></label><button className="btn primary full" disabled={loading}>{loading?'Signing in...':'Login'}</button></form><p className="muted">New student? <Link to="/register">Create an account</Link></p></div></div>
}

function Register({onLogin}) {
  const nav = useNavigate(); const [branches,setBranches]=useState([]); const [form,setForm]=useState({name:'',email:'',password:'',branchId:'',semester:''}); const [error,setError]=useState(''); const [loading,setLoading]=useState(false)
  useEffect(()=>{api('/branches').then(d=>setBranches(d.branches)).catch(()=>{})},[])
  const submit=async e=>{e.preventDefault();setError('');setLoading(true);try{const d=await api('/auth/register',{method:'POST',body:JSON.stringify(form)});setSession(d);onLogin(d.user);nav('/branchhub')}catch(err){setError(err.message)}finally{setLoading(false)}}
  return <div className="auth-wrap"><div className="auth-card wide"><span className="eyebrow">JOIN THE CAMPUS</span><h1>Create your student account</h1><p>Pick your branch now; you can personalize resources later.</p>{error&&<div className="error">{error}</div>}<GoogleSignInButton onError={setError}/><div className="auth-divider">or create an account with email</div><form onSubmit={submit} className="form two"><label>Full Name<input value={form.name} onChange={e=>setForm({...form,name:e.target.value})} required/></label><label>Email<input type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} required/></label><label>Password<input type="password" minLength="6" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} required/></label><label>Semester<input type="number" min="1" max="12" value={form.semester} onChange={e=>setForm({...form,semester:e.target.value})}/></label><label className="span-2">Branch<select value={form.branchId} onChange={e=>setForm({...form,branchId:e.target.value})}><option value="">Select branch</option>{branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label><button className="btn primary full span-2" disabled={loading}>{loading?'Creating...':'Create account'}</button></form><p className="muted">Already have an account? <Link to="/login">Login</Link></p></div></div>
}

function GoogleAuthCallback({onLogin}) {
  const nav=useNavigate()
  const [branches,setBranches]=useState([])
  const [profile,setProfile]=useState({branchId:'',semester:''})
  const [accessToken,setAccessToken]=useState('')
  const [supabaseClient,setSupabaseClient]=useState(null)
  const [error,setError]=useState('')
  const [loading,setLoading]=useState(true)

  useEffect(()=>{
    let active=true
    let authClient=null
    const finishSignIn=async()=>{
      const authModule=await import('./lib/supabase')
      authClient=authModule.supabase
      if(!authClient)throw new Error('Google sign-in is not configured. Add the Supabase client settings and enable Google in Supabase Auth.')
      if(active)setSupabaseClient(authClient)
      const {data,error:sessionError}=await authClient.auth.getSession()
      if(sessionError)throw sessionError
      const token=data.session?.access_token
      if(!token)throw new Error('Google sign-in was cancelled or expired. Please try again.')
      const result=await api('/auth/google',{method:'POST',body:JSON.stringify({accessToken:token})})
      if(result.profileRequired){
        const branchData=await api('/branches')
        if(active){setAccessToken(token);setBranches(branchData.branches);setLoading(false)}
        return
      }
      if(active){
        setSession(result)
        onLogin(result.user)
        clearGoogleSessionInBackground(authClient)
        nav(result.user.role==='admin'||result.user.role==='super_admin'||result.user.role==='teacher'||result.user.role==='moderator'?'/admin':'/branchhub',{replace:true})
      }
    }
    finishSignIn().catch(async err=>{
      if(active){setError(err.data?.message||err.message);setLoading(false)}
      if(authClient)clearGoogleSessionInBackground(authClient)
    })
    return ()=>{active=false}
  },[nav,onLogin])

  const completeProfile=async event=>{
    event.preventDefault()
    setError('')
    setLoading(true)
    try{
      const result=await api('/auth/google',{method:'POST',body:JSON.stringify({
        accessToken,
        branchId:profile.branchId,
        semester:profile.semester||null
      })})
      if(result.profileRequired)throw new Error('Select your branch to finish creating the account.')
      setSession(result)
      onLogin(result.user)
      clearGoogleSessionInBackground(supabaseClient)
      nav('/branchhub',{replace:true})
    }catch(err){setError(err.data?.message||err.message)}
    finally{setLoading(false)}
  }

  return <div className="auth-wrap"><div className="auth-card"><span className="eyebrow">GOOGLE SIGN-IN</span><h1>{accessToken?'Finish your student profile':'Signing you in'}</h1>{accessToken?<><p>Choose your branch so CampusHub can show the right tools and subjects.</p>{error&&<div className="error" role="alert">{error}</div>}<form className="form" onSubmit={completeProfile}><label>Branch<select value={profile.branchId} onChange={event=>setProfile({...profile,branchId:event.target.value})} required><option value="">Select your branch</option>{branches.map(branch=><option key={branch.id} value={branch.id}>{branch.name}</option>)}</select></label><label>Semester (optional)<input type="number" min="1" max="12" value={profile.semester} onChange={event=>setProfile({...profile,semester:event.target.value})}/></label><button className="btn primary full" disabled={loading}>{loading?'Creating account...':'Finish account setup'}</button></form></>:<>{error&&<div className="error" role="alert">{error}</div>}{!error&&<p>Please wait while Google verifies your account.</p>}</>}{error&&<p className="muted"><Link to="/login">Return to login</Link></p>}</div></div>
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
  const [skills,setSkills]=useState([]),[branches,setBranches]=useState([]),[requests,setRequests]=useState([])
  const [q,setQ]=useState(''),[branchFilter,setBranchFilter]=useState(''),[typeFilter,setTypeFilter]=useState('teach'),[levelFilter,setLevelFilter]=useState('')
  const [form,setForm]=useState({skillName:'',type:'teach',level:'beginner'}),[offerSkillId,setOfferSkillId]=useState(''),[requestMessage,setRequestMessage]=useState('')
  const [feedbackForms,setFeedbackForms]=useState({}),[msg,setMsg]=useState(''),[loading,setLoading]=useState(false)
  const loadSkills=()=>api('/skills').then(d=>setSkills(d.skills)).catch(err=>setMsg(err.message))
  const loadRequests=()=>user?api('/user/skill-requests').then(d=>setRequests(d.requests)).catch(err=>setMsg(err.message)):Promise.resolve()
  useEffect(()=>{api('/branches').then(d=>setBranches(d.branches)).catch(err=>setMsg(err.message));loadSkills()},[])
  useEffect(()=>{loadRequests()},[user?.id])
  const mySkills=skills.filter(skill=>String(skill.user_id)===String(user?.id))
  const myTeaching=mySkills.filter(skill=>skill.type==='teach')
  const wanted=mySkills.filter(skill=>skill.type==='learn')
  const matches=skills.filter(skill=>skill.type==='teach'&&String(skill.user_id)!==String(user?.id)).map(skill=>{
    const learning=wanted.find(item=>item.skill_name.trim().toLowerCase()===skill.skill_name.trim().toLowerCase())
    if(!learning)return null
    const candidateOffers=skills.filter(item=>String(item.user_id)===String(skill.user_id)&&item.type==='learn')
    const exchangeOffer=myTeaching.find(item=>candidateOffers.some(candidate=>candidate.skill_name.trim().toLowerCase()===item.skill_name.trim().toLowerCase()))
    return {skill,learning,exchangeOffer}
  }).filter(Boolean)
  const visibleSkills=skills.filter(skill=>{
    const matchesQuery=!q||`${skill.skill_name} ${skill.name} ${skill.branch||''}`.toLowerCase().includes(q.toLowerCase())
    return matchesQuery&&(!branchFilter||skill.branch===branchFilter)&&(!typeFilter||skill.type===typeFilter)&&(!levelFilter||skill.level===levelFilter)
  })
  const add=async e=>{
    e.preventDefault();setMsg('')
    if(!user){setMsg('Log in to publish a skill.');return}
    setLoading(true)
    try{await api('/user/skills',{method:'POST',body:JSON.stringify(form)});setForm({skillName:'',type:'teach',level:'beginner'});setMsg('Skill added to your profile.');await loadSkills()}
    catch(err){setMsg(err.message)}
    finally{setLoading(false)}
  }
  const sendRequest=async skillId=>{
    if(!user){setMsg('Log in to send a SkillSwap request.');return}
    setMsg('')
    try{await api('/user/skill-requests',{method:'POST',body:JSON.stringify({skillId,offeredSkillId:offerSkillId||null,message:requestMessage})});setRequestMessage('');setMsg('Learning request sent. The student can accept or decline it.');await loadRequests()}
    catch(err){setMsg(err.message)}
  }
  const updateRequest=async(id,action)=>{
    setMsg('')
    try{await api(`/user/skill-requests/${id}`,{method:'PATCH',body:JSON.stringify({action})});await loadRequests()}
    catch(err){setMsg(err.message)}
  }
  const submitFeedback=async request=>{
    const formValue=feedbackForms[request.id]||{rating:'5',comment:''}
    setMsg('')
    try{await api(`/user/skill-requests/${request.id}/feedback`,{method:'POST',body:JSON.stringify({rating:Number(formValue.rating),comment:formValue.comment})});setMsg('Feedback saved.');await loadRequests();await loadSkills()}
    catch(err){setMsg(err.message)}
  }
  const ratingForm=request=>feedbackForms[request.id]||{rating:'5',comment:''}
  return <div><PageHeader eyebrow="SKILLSWAP" title="Teach one skill. Learn another." text="Find peers across branches, make a learning request, and offer a skill in return if you want to trade."/>
    {msg&&<div className="container"><div className="notice" role="status">{msg}</div></div>}
    <section className="container section split">
      <div className="panel">
        <span className="eyebrow">MATCHES FOR YOU</span>
        {user&&matches.length?<div className="skill-grid">{matches.map(({skill,learning,exchangeOffer})=><article className="skill-card" key={`match-${skill.id}`}><div><span className="tag">{exchangeOffer?'COMPLEMENTARY EXCHANGE':'MATCHES YOUR LEARNING LIST'}</span><h3>{skill.skill_name}</h3><p>{skill.name} · {skill.branch||'General'} · {skill.level}</p><small>You want to learn {learning.skill_name}{exchangeOffer?` · You can offer ${exchangeOffer.skill_name} in return`:''}</small></div><button className="btn small" onClick={()=>sendRequest(skill.id)}>Request</button></article>)}</div>:<Empty text={user?'Add a skill you want to learn to see relevant peer matches.':'Log in and publish skills to get personal matches.'}/>}
        {myTeaching.length>0&&<label>Offer in exchange<select value={offerSkillId} onChange={e=>setOfferSkillId(e.target.value)}><option value="">No exchange offer</option>{myTeaching.map(skill=><option value={skill.id} key={skill.id}>{skill.skill_name} · {skill.level}</option>)}</select></label>}
        <label className="form">Optional request message<textarea maxLength="500" value={requestMessage} onChange={e=>setRequestMessage(e.target.value)} placeholder="What would you like to learn? Suggest a time or format."/></label>
        <span className="muted">Profiles show only a student's name and branch. Contact details are not exposed.</span>
        <span className="eyebrow">DISCOVER SKILLS</span>
        <label className="search-box big"><span className="search-label">SEARCH</span><input placeholder="Python, AutoCAD, SQL..." value={q} onChange={e=>setQ(e.target.value)}/></label>
        <div className="form two"><label>Branch<select value={branchFilter} onChange={e=>setBranchFilter(e.target.value)}><option value="">All branches</option>{branches.map(branch=><option key={branch.id}>{branch.name}</option>)}</select></label><label>Listing<select value={typeFilter} onChange={e=>setTypeFilter(e.target.value)}><option value="teach">Skills to learn</option><option value="learn">Skills students want</option><option value="">All listings</option></select></label><label>Proficiency<select value={levelFilter} onChange={e=>setLevelFilter(e.target.value)}><option value="">Any level</option><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label></div>
        <div className="skill-grid">{visibleSkills.map(skill=><article className="skill-card" key={skill.id}><div><span className="tag">{skill.type==='teach'?'TEACHES':'WANTS TO LEARN'}</span><h3>{skill.skill_name}</h3><p>{skill.name} · {skill.branch||'General'}</p><small>{skill.level}{skill.review_count>0?` · ${skill.average_rating}/5 (${skill.review_count} reviews)`:''}</small></div>{skill.type==='teach'&&String(skill.user_id)!==String(user?.id)&&(user?<button className="btn small" onClick={()=>sendRequest(skill.id)}>Request</button>:<Link className="btn small" to="/login">Log in</Link>)}</article>)}{!visibleSkills.length&&<Empty text="No skill listings match these filters yet."/>}</div>
      </div>
      <div className="panel">
        <span className="eyebrow">MY SKILLS</span><h2>Build your skill profile</h2><p className="muted">Add separate teach and learn listings; other students can discover matching skills without seeing private contact details.</p>
        <form className="form" onSubmit={add}><label>Skill<input maxLength="80" value={form.skillName} onChange={e=>setForm({...form,skillName:e.target.value})} placeholder="Python" required/></label><label>I want to<select value={form.type} onChange={e=>setForm({...form,type:e.target.value})}><option value="teach">Teach it</option><option value="learn">Learn it</option></select></label><label>My proficiency<select value={form.level} onChange={e=>setForm({...form,level:e.target.value})}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label><button className="btn primary full" disabled={loading}>{loading?'Publishing...':'Publish skill'}</button></form>
        <div className="skill-grid">{mySkills.map(skill=><article className="skill-card" key={`mine-${skill.id}`}><div><span className="tag">{skill.type==='teach'?'I CAN TEACH':'I WANT TO LEARN'}</span><h3>{skill.skill_name}</h3><small>{skill.level}</small></div></article>)}{user&&!mySkills.length&&<Empty text="Your published skills will appear here."/>}{!user&&<Empty text="Log in to create your own teach/learn profile."/>}</div>
        <span className="eyebrow">LEARNING REQUESTS</span>
        {requests.length?<div className="skill-grid">{requests.map(request=><article className="skill-card" key={`request-${request.id}`}><div><span className="tag">{request.direction.toUpperCase()} · {request.status.toUpperCase()}</span><h3>{request.skill_name}</h3><p>{request.direction==='received'?`${request.requester_name} · ${request.requester_branch||'General'}`:`${request.owner_name} · ${request.owner_branch||'General'}`}</p>{request.offered_skill_name&&<small>Offer: {request.offered_skill_name}</small>}<p>{request.message}</p></div>
          {request.direction==='received'&&request.status==='pending'&&<div><button className="btn small" onClick={()=>updateRequest(request.id,'accept')}>Accept</button><button className="btn small" onClick={()=>updateRequest(request.id,'reject')}>Decline</button></div>}
          {request.status==='accepted'&&<div><p className="muted">{request.direction==='received'?(request.owner_completed_at?'You confirmed completion.':'The other student accepted. Coordinate safely on campus; personal contact details stay private.'):(request.requester_completed_at?'You confirmed completion.':'The other student accepted. Coordinate safely on campus; personal contact details stay private.')}</p>{!(request.direction==='received'?request.owner_completed_at:request.requester_completed_at)&&<button className="btn small" onClick={()=>updateRequest(request.id,'confirm-completed')}>Confirm completed</button>}</div>}
          {request.status==='completed'&&!request.my_feedback_id&&<div className="form"><label>Rate this exchange<select value={ratingForm(request).rating} onChange={e=>setFeedbackForms({...feedbackForms,[request.id]:{...ratingForm(request),rating:e.target.value}})}><option value="5">5 — Great</option><option value="4">4 — Good</option><option value="3">3 — Okay</option><option value="2">2 — Poor</option><option value="1">1 — Very poor</option></select></label><label>Feedback<textarea maxLength="500" value={ratingForm(request).comment} onChange={e=>setFeedbackForms({...feedbackForms,[request.id]:{...ratingForm(request),comment:e.target.value}})}/></label><button className="btn small" onClick={()=>submitFeedback(request)}>Submit feedback</button></div>}
          {request.my_feedback_id&&<small>You left feedback for this exchange.</small>}
        </article>)}</div>:<Empty text={user?'Your sent and received requests will appear here.':'Log in to manage learning requests.'}/>}
      </div>
    </section>
  </div>
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
    percentage:{title:'Percentage Calculator'},cgpa:{title:'CGPA Calculator'},units:{title:'Unit Converter'},python:{title:'Python Playground'},sql:{title:'SQL Query Practice'},linux:{title:'Linux Command Helper'},subnet:{title:'IP / Subnet Calculator'},'ohms-law':{title:"Ohm's Law Calculator"},power:{title:'Power Calculator'},'logic-gates':{title:'Logic Gate Helper'},'mechanical-units':{title:'Mechanical Unit Converter'},'area-volume':{title:'Area & Volume Calculator'},'mlt-dilution':{title:'Solution Dilution Calculator'},compiler:{title:'Multilingual Code Lab'},'project-ideas':{title:'Project Idea Generator'}
  }
  const meta=configs[tool]||{title:'Campus Tool'}
  const tools={
    percentage:<PercentageTool/>,
    cgpa:<CgpaTool/>,
    units:<UnitConverterTool/>,
    python:<PythonPracticeTool/>,
    sql:<SqlPracticeTool/>,
    linux:<LinuxTool/>,
    subnet:<SubnetTool/>,
    'ohms-law':<OhmTool/>,
    power:<PowerTool/>,
    'logic-gates':<LogicTool/>,
    'mechanical-units':<MechanicalUnitTool/>,
    'area-volume':<AreaTool/>,
    'mlt-dilution':<MltDilutionTool/>,
    compiler:<Compiler/>,
    'project-ideas':<ProjectIdeas/>
  }
  return <div><PageHeader eyebrow="MINI TOOLS LAB" title={meta.title} text="Practical, browser-based tools for learning and everyday calculations."/><div className="container section"><div className="tool-workspace">{tools[tool]||<ComingTool title={meta.title}/>}</div></div></div>
}
function requireParams(){ const p=location.pathname.split('/').filter(Boolean); return {tool:p[1]||''} }
function PercentageTool(){const [a,setA]=useState(''),[b,setB]=useState('');const r=a&&b?((Number(a)/Number(b))*100).toFixed(2):'—';return <SimpleCalc title="What percent is A of B?" fields={[['A',a,setA],['B',b,setB]]} result={`${r}%`}/>}
function CgpaTool(){const [vals,setVals]=useState('8,7.5,9,8.2');const arr=vals.split(',').map(Number).filter(n=>Number.isFinite(n));const r=arr.length?(arr.reduce((a,b)=>a+b,0)/arr.length).toFixed(2):'—';return <div className="simple-tool"><h2>CGPA</h2><p>Enter semester/subject GPAs separated by commas.</p><input value={vals} onChange={e=>setVals(e.target.value)}/><div className="result"><span>Average</span><strong>{r}</strong></div></div>}
function OhmTool(){const [v,setV]=useState(''),[i,setI]=useState(''),[r,setR]=useState('');const values=[v,i,r].map(value=>value===''?null:Number(value));const filled=values.filter(value=>value!==null).length;let res='Enter any two values';if(filled===2){const [voltage,current,resistance]=values;if(voltage!==null&&current!==null)res=resistance===0?'Resistance cannot be zero':`R = ${(voltage/current).toFixed(3)} Ω · P = ${(voltage*current).toFixed(3)} W`;else if(voltage!==null&&resistance!==null)resistance===0?res='Resistance cannot be zero':res=`I = ${(voltage/resistance).toFixed(3)} A · P = ${(voltage*voltage/resistance).toFixed(3)} W`;else if(current!==null&&resistance!==null)res=`V = ${(current*resistance).toFixed(3)} V · P = ${(current*current*resistance).toFixed(3)} W`;}return <div className="simple-tool"><h2>Ohm's Law</h2><p>Enter any two values to calculate the third and electrical power.</p><div className="three-inputs"><label>Voltage (V)<input type="number" min="0" step="any" value={v} onChange={e=>setV(e.target.value)}/></label><label>Current (A)<input type="number" min="0" step="any" value={i} onChange={e=>setI(e.target.value)}/></label><label>Resistance (Ω)<input type="number" min="0" step="any" value={r} onChange={e=>setR(e.target.value)}/></label></div><div className="result"><span>Result</span><strong>{res}</strong></div></div>}
function PowerTool(){const [v,setV]=useState(''),[i,setI]=useState('');const p=v&&i?(Number(v)*Number(i)).toFixed(2):'—';return <SimpleCalc title="DC power: P = V × I" fields={[['Voltage (V)',v,setV],['Current (A)',i,setI]]} result={`${p} W`}/>}
function AreaTool(){
  const [shape,setShape]=useState('rectangle'),[a,setA]=useState(''),[b,setB]=useState(''),[c,setC]=useState('')
  const x=Number(a),y=Number(b),z=Number(c)
  const dimensionsValid=a!==''&&Number.isFinite(x)&&x>0
  let result='Enter the dimensions'
  if(dimensionsValid&&shape==='circle')result=`Area: ${(Math.PI*x*x).toFixed(3)} square units`
  else if(dimensionsValid&&shape==='rectangle'&&b!==''&&Number.isFinite(y)&&y>0)result=`Area: ${(x*y).toFixed(3)} square units`
  else if(dimensionsValid&&shape==='triangle'&&b!==''&&Number.isFinite(y)&&y>0)result=`Area: ${(x*y/2).toFixed(3)} square units`
  else if(dimensionsValid&&shape==='cylinder'&&b!==''&&Number.isFinite(y)&&y>0)result=`Volume: ${(Math.PI*x*x*y).toFixed(3)} cubic units`
  else if(dimensionsValid&&shape==='box'&&b!==''&&c!==''&&Number.isFinite(y)&&Number.isFinite(z)&&y>0&&z>0)result=`Volume: ${(x*y*z).toFixed(3)} cubic units`
  return <div className="simple-tool"><h2>Area & Volume</h2><label>Shape<select value={shape} onChange={e=>setShape(e.target.value)}><option value="rectangle">Rectangle</option><option value="triangle">Triangle</option><option value="circle">Circle</option><option value="box">Rectangular prism</option><option value="cylinder">Cylinder</option></select></label><div className="three-inputs"><label>{shape==='circle'||shape==='cylinder'?'Radius':'Length / base'}<input type="number" min="0" step="any" value={a} onChange={e=>setA(e.target.value)}/></label>{shape!=='circle'&&<label>{shape==='box'?'Width':'Height / width'}<input type="number" min="0" step="any" value={b} onChange={e=>setB(e.target.value)}/></label>}{shape==='box'&&<label>Height<input type="number" min="0" step="any" value={c} onChange={e=>setC(e.target.value)}/></label>}</div><div className="result"><span>Result</span><strong>{result}</strong></div><p>Dimensions use consistent units; area is in square units and volume in cubic units.</p></div>
}
function LogicTool(){const [a,setA]=useState(false),[b,setB]=useState(false);const rows=[[false,false],[false,true],[true,false],[true,true]];return <div className="simple-tool"><h2>Logic Gates</h2><p>Toggle inputs to inspect gate outputs, or use the truth table below.</p><div className="logic-inputs"><label><input type="checkbox" checked={a} onChange={e=>setA(e.target.checked)}/> A</label><label><input type="checkbox" checked={b} onChange={e=>setB(e.target.checked)}/> B</label></div><div className="logic-results"><span>AND: {a&&b?1:0}</span><span>OR: {a||b?1:0}</span><span>NAND: {a&&b?0:1}</span><span>XOR: {a!==b?1:0}</span><span>NOT A: {a?0:1}</span><span>NOT B: {b?0:1}</span></div><div className="resource-list">{rows.map(([left,right])=><article className="resource" key={`${left}-${right}`}><span>A={Number(left)} · B={Number(right)}</span><span>AND {Number(left&&right)} · OR {Number(left||right)} · XOR {Number(left!==right)}</span></article>)}</div></div>}
function LinuxTool(){return <div className="simple-tool"><h2>Linux Command Helper</h2><div className="cmd-grid">{[['ls','List files'],['cd','Change directory'],['pwd','Show current directory'],['mkdir','Create directory'],['cp','Copy files'],['mv','Move/rename files'],['rm','Remove files'],['grep','Search text']].map(([c,d])=><div className="cmd" key={c}><code>{c}</code><span>{d}</span></div>)}</div></div>}
const pythonExercises=[
  {prompt:'What does this print?  x = 3; print(x * 2)',options:['6','33','Error'],answer:'6',explanation:'The integer value 3 is multiplied by 2.'},
  {prompt:'Which values are produced by range(3)?',options:['1, 2, 3','0, 1, 2','0, 1, 2, 3'],answer:'0, 1, 2',explanation:'range(3) starts at zero and stops before three.'},
  {prompt:'What does "campus".upper() return?',options:['campus','CAMPUS','Campus'],answer:'CAMPUS',explanation:'upper() returns a copy of the string with letters in uppercase.'}
]
function PythonPracticeTool(){const [index,setIndex]=useState(0),[answer,setAnswer]=useState(''),[checked,setChecked]=useState(false);const exercise=pythonExercises[index];return <div className="simple-tool"><h2>Python Basics Practice</h2><p>Check your understanding of Python expressions and core behavior. This practice tool does not execute arbitrary code.</p><label>Exercise<select value={index} onChange={e=>{setIndex(Number(e.target.value));setAnswer('');setChecked(false)}}>{pythonExercises.map((item,i)=><option key={i} value={i}>Exercise {i+1}</option>)}</select></label><p>{exercise.prompt}</p><div className="form">{exercise.options.map(option=><label key={option}><span><input type="radio" name="python-answer" value={option} checked={answer===option} onChange={()=>{setAnswer(option);setChecked(false)}}/> {option}</span></label>)}</div><button className="btn primary" disabled={!answer} onClick={()=>setChecked(true)}>Check answer</button>{checked&&<div className={answer===exercise.answer?'notice':'error'}>{answer===exercise.answer?'Correct. ':'Not quite. '}{exercise.explanation}</div>}</div>}
function parseIPv4(value){const parts=value.trim().split('.');if(parts.length!==4||parts.some(part=>!/^\d{1,3}$/.test(part)||Number(part)>255))return null;return parts.reduce((acc,part)=>(acc<<8n)|BigInt(Number(part)),0n)}
function formatIPv4(value){return [24n,16n,8n,0n].map(shift=>Number((value>>shift)&255n)).join('.')}
function SubnetTool(){const [address,setAddress]=useState('192.168.1.10'),[prefix,setPrefix]=useState('24');const [result,setResult]=useState(null),[error,setError]=useState('');const calculate=e=>{e.preventDefault();const ip=parseIPv4(address),bits=Number(prefix);if(ip===null||!Number.isInteger(bits)||bits<0||bits>32){setResult(null);setError('Enter a valid IPv4 address and a prefix from 0 to 32.');return}const all=0xffffffffn,mask=bits===0?0n:(all<<(32n-BigInt(bits)))&all,network=ip&mask,broadcast=network|(all^mask),total=2**(32-bits),usable=bits>=31?total:Math.max(0,total-2);setError('');setResult({mask:formatIPv4(mask),network:formatIPv4(network),broadcast:formatIPv4(broadcast),total:total.toLocaleString(),usable:usable.toLocaleString(),first:bits>=31?formatIPv4(network):formatIPv4(network+1n),last:bits>=31?formatIPv4(broadcast):formatIPv4(broadcast-1n)})};return <div className="simple-tool"><h2>IPv4 Subnet Calculator</h2><p>Calculate the network range from an IPv4 address and CIDR prefix.</p><form className="form two" onSubmit={calculate}><label>IPv4 address<input value={address} onChange={e=>setAddress(e.target.value)} required/></label><label>CIDR prefix<input type="number" min="0" max="32" value={prefix} onChange={e=>setPrefix(e.target.value)} required/></label><button className="btn primary">Calculate subnet</button></form>{error&&<div className="error">{error}</div>}{result&&<div className="resource-list"><article className="resource"><strong>Subnet mask</strong><span>{result.mask}</span></article><article className="resource"><strong>Network</strong><span>{result.network}</span></article><article className="resource"><strong>Broadcast</strong><span>{result.broadcast}</span></article><article className="resource"><strong>Address range</strong><span>{result.first} – {result.last}</span></article><article className="resource"><strong>Addresses</strong><span>{result.usable} usable / {result.total} total</span></article></div>}</div>}
const unitGroups={length:{'metres (m)':1,'kilometres (km)':1000,'centimetres (cm)':0.01,'millimetres (mm)':0.001,'feet (ft)':0.3048,'inches (in)':0.0254},mass:{'kilograms (kg)':1,'grams (g)':0.001,'tonnes (t)':1000,'pounds (lb)':0.45359237},pressure:{'pascal (Pa)':1,'kilopascal (kPa)':1000,'megapascal (MPa)':1e6,bar:1e5,'pounds per square inch (psi)':6894.757293},force:{newton:1,'kilonewton (kN)':1000,'pound-force (lbf)':4.448221615},torque:{'newton-metre (N·m)':1,'kilonewton-metre (kN·m)':1000,'pound-foot (lbf·ft)':1.355817948},power:{watt:1,'kilowatt (kW)':1000,'horsepower (hp)':745.699872},speed:{'metres per second (m/s)':1,'kilometres per hour (km/h)':1/3.6,'feet per second (ft/s)':0.3048},temperature:{'Celsius (°C)':'C','Fahrenheit (°F)':'F','Kelvin (K)':'K'}}
function convertUnit(value,category,from,to){if(category==='temperature'){const c=from==='C'?value:from==='F'?(value-32)*5/9:value-273.15;return to==='C'?c:to==='F'?c*9/5+32:c+273.15}return value*unitGroups[category][from]/unitGroups[category][to]}
function UnitConverterTool({mechanical=false}){const groups=mechanical?['pressure','force','torque','power','speed']:['length','mass','temperature'];const [category,setCategory]=useState(groups[0]),[value,setValue]=useState('1');const units=unitGroups[category]||unitGroups[groups[0]];const [from,setFrom]=useState(Object.keys(units)[0]),[to,setTo]=useState(Object.keys(units)[1]);const chooseCategory=next=>{setCategory(next);setFrom(Object.keys(unitGroups[next])[0]);setTo(Object.keys(unitGroups[next])[1])};const result=value!==''&&Number.isFinite(Number(value))?convertUnit(Number(value),category,from,to):null;return <div className="simple-tool"><h2>{mechanical?'Mechanical Engineering':'Study'} Unit Converter</h2><div className="form two"><label>Quantity<select value={category} onChange={e=>chooseCategory(e.target.value)}>{groups.map(group=><option key={group} value={group}>{group[0].toUpperCase()+group.slice(1)}</option>)}</select></label><label>Value<input type="number" step="any" value={value} onChange={e=>setValue(e.target.value)}/></label><label>From<select value={from} onChange={e=>setFrom(e.target.value)}>{Object.keys(units).map(unit=><option key={unit}>{unit}</option>)}</select></label><label>To<select value={to} onChange={e=>setTo(e.target.value)}>{Object.keys(units).map(unit=><option key={unit}>{unit}</option>)}</select></label></div><div className="result"><span>Converted value</span><strong>{result===null?'Enter a number':Number(result.toPrecision(8)).toLocaleString()}</strong></div></div>}
function MechanicalUnitTool(){return <UnitConverterTool mechanical/>}
function MltDilutionTool(){const [stock,setStock]=useState(''),[stockVolume,setStockVolume]=useState(''),[target,setTarget]=useState(''),[finalVolume,setFinalVolume]=useState('');const fields=[stock,stockVolume,target,finalVolume];const known=fields.map((v,i)=>v!==''?i:-1).filter(i=>i>=0);let output='Enter any three positive values to calculate the fourth.';if(known.length===3&&fields.every((v,i)=>v===''||Number(v)>0)){const [c1,v1,c2,v2]=fields.map(Number);const missing=fields.findIndex(v=>v==='');if(missing===0&&v1>0)output=`Stock concentration: ${(c2*v2/v1).toPrecision(6)}`;else if(missing===1&&c1>0)output=`Stock volume needed: ${(c2*v2/c1).toPrecision(6)}`;else if(missing===2&&v2>0)output=`Target concentration: ${(c1*v1/v2).toPrecision(6)}`;else if(missing===3&&c2>0)output=`Final volume: ${(c1*v1/c2).toPrecision(6)}`;else output='Values must be greater than zero.';}return <div className="simple-tool"><h2>Solution Dilution (C₁V₁ = C₂V₂)</h2><p>For academic laboratory calculations only. Use consistent concentration and volume units; verify protocols with your instructor.</p><div className="form two"><label>Stock concentration (C₁)<input type="number" min="0" step="any" value={stock} onChange={e=>setStock(e.target.value)}/></label><label>Stock volume (V₁)<input type="number" min="0" step="any" value={stockVolume} onChange={e=>setStockVolume(e.target.value)}/></label><label>Target concentration (C₂)<input type="number" min="0" step="any" value={target} onChange={e=>setTarget(e.target.value)}/></label><label>Final volume (V₂)<input type="number" min="0" step="any" value={finalVolume} onChange={e=>setFinalVolume(e.target.value)}/></label></div><div className="result"><span>Calculated value</span><strong>{output}</strong></div></div>}
function SqlPracticeTool(){
  const examples={
    select:'SELECT name, branch FROM students WHERE semester = 4 ORDER BY name;',
    join:'SELECT students.name, branches.name AS branch\nFROM students\nJOIN branches ON students.branch_id = branches.id;',
    aggregate:'SELECT branch_id, COUNT(*) AS student_count\nFROM students\nGROUP BY branch_id;'
  }
  const [example,setExample]=useState('select'),[query,setQuery]=useState(examples.select)
  const formatted=query.trim()
    .replace(/\s+/g,' ')
    .replace(/\b(FROM|WHERE|JOIN|LEFT JOIN|RIGHT JOIN|INNER JOIN|ON|GROUP BY|ORDER BY|HAVING|LIMIT|VALUES|SET)\b/gi,word=>`\n${word.toUpperCase()}`)
    .replace(/\b(SELECT|INSERT INTO|UPDATE|DELETE FROM|AS|AND|OR|DESC|ASC)\b/gi,word=>word.toUpperCase())
    .trim()
  return <div className="simple-tool"><h2>SQL Query Practice</h2><p>Write or format practice queries. CampusHub does not execute this SQL or send it to the database.</p><label>Example<select value={example} onChange={e=>{setExample(e.target.value);setQuery(examples[e.target.value])}}><option value="select">Filter and sort</option><option value="join">Join tables</option><option value="aggregate">Group and count</option></select></label><label>Your query<textarea rows="8" spellCheck="false" value={query} onChange={e=>setQuery(e.target.value)}/></label><div className="result"><span>Formatted preview</span><pre>{formatted||'Your formatted query will appear here.'}</pre></div><p>Use this workspace to practice SQL structure. Query results are not generated.</p></div>
}
function ComingTool({title}){return <div className="simple-tool"><h2>{title}</h2><p>This route is wired into CampusHub and ready for a richer calculator/simulator. The current starter keeps the core platform working without paid APIs.</p><div className="notice">Next development step: add the branch-specific algorithm here and connect it from BranchHub.</div></div>}
function SimpleCalc({title,fields,result}){return <div className="simple-tool"><h2>{title}</h2><div className="three-inputs">{fields.map(([label,v,setV])=><label key={label}>{label}<input value={v} onChange={e=>setV(e.target.value)} inputMode="decimal"/></label>)}</div><div className="result"><span>Result</span><strong>{result}</strong></div></div>}

createRoot(document.getElementById('root')).render(<BrowserRouter><App/></BrowserRouter>)
