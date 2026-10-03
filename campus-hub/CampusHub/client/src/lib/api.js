import { defaultDemoState } from './demo-data.js'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'
const USE_DEMO_FALLBACK = import.meta.env.DEV && !import.meta.env.VITE_API_URL
const DEMO_KEY = 'campushub_demo_data'

function getDemoState() {
  try {
    const raw = localStorage.getItem(DEMO_KEY)
    if (raw) return JSON.parse(raw)
  } catch {
    // noop
  }
  localStorage.setItem(DEMO_KEY, JSON.stringify(defaultDemoState))
  return defaultDemoState
}

function setDemoState(nextState) {
  localStorage.setItem(DEMO_KEY, JSON.stringify(nextState))
}

function getBranchName(branchId) {
  const branches = getDemoState().branches
  const branch = branches.find(item => Number(item.id) === Number(branchId))
  return branch ? branch.name : ''
}

function sanitizeUser(user) {
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    role: user.role,
    branch_id: user.branch_id || null,
    semester: user.semester || null,
    bio: user.bio || '',
    branch_name: getBranchName(user.branch_id)
  }
}

function readBody(options) {
  if (!options.body) return null
  if (options.body instanceof FormData) {
    return Object.fromEntries(options.body.entries())
  }
  if (typeof options.body === 'string') {
    try { return JSON.parse(options.body) } catch { return options.body }
  }
  return options.body
}

function mockApi(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const rawPath = path.split('?')[0]
  const query = new URLSearchParams(path.split('?')[1] || '')
  const state = getDemoState()

  if (rawPath === '/auth/login') {
    const body = readBody(options)
    const user = state.users.find(item => item.email.toLowerCase() === String(body.email || '').trim().toLowerCase())
    const password = String(body.password || '')
    const demoAdminPassword = user?.role === 'admin' && user.email === 'admin@campushub.local' && password === 'ChangeMe123!'
    if (!user || (user.password_hash !== password && !demoAdminPassword)) {
      throw new Error('Invalid email or password')
    }
    const token = `demo-token-${user.id}-${Date.now()}`
    const safeUser = sanitizeUser(user)
    return { token, user: safeUser }
  }

  if (rawPath === '/auth/register') {
    const body = readBody(options)
    const email = String(body.email || '').trim().toLowerCase()
    if (!body.name || !body.email || !body.password) throw new Error('Name, email and password are required')
    if (body.password.length < 6) throw new Error('Password must be at least 6 characters')
    if (state.users.some(user => user.email.toLowerCase() === email)) throw new Error('Email already registered')
    const user = {
      id: Date.now(),
      name: String(body.name).trim(),
      email,
      password_hash: String(body.password),
      role: 'student',
      branch_id: body.branchId ? Number(body.branchId) : null,
      semester: body.semester ? Number(body.semester) : null,
      bio: ''
    }
    state.users.push(user)
    setDemoState(state)
    const token = `demo-token-${user.id}-${Date.now()}`
    return { token, user: sanitizeUser(user) }
  }

  if (rawPath === '/auth/me') {
    const token = getToken()
    const userId = Number(String(token || '').split('-')[2])
    const user = state.users.find(item => Number(item.id) === Number(userId))
    if (!user) throw new Error('User not found')
    return { user: sanitizeUser(user) }
  }

  if (rawPath === '/branches') {
    return { branches: state.branches }
  }

  if (rawPath === '/subjects') {
    const branchId = query.get('branchId')
    const subjects = branchId ? state.subjects.filter(item => Number(item.branch_id) === Number(branchId)) : state.subjects
    return { subjects: subjects.map(subject => ({ ...subject, branch_name: getBranchName(subject.branch_id) })) }
  }

  if (rawPath === '/notes') {
    const branchId = query.get('branchId')
    const subjectId = query.get('subjectId')
    const q = (query.get('q') || '').trim().toLowerCase()
    const notes = state.notes.filter(item => {
      const matchBranch = !branchId || Number(item.subject_id) === Number(subjectId) || (state.subjects.find(subject => Number(subject.id) === Number(item.subject_id))?.branch_id === Number(branchId))
      const matchSubject = !subjectId || Number(item.subject_id) === Number(subjectId)
      const searchText = `${item.title} ${item.description} ${item.subject}`.toLowerCase()
      const matchQuery = !q || searchText.includes(q)
      return matchBranch && matchSubject && matchQuery
    })
    return { notes }
  }

  if (rawPath === '/tools') {
    const branchId = query.get('branchId')
    const q = (query.get('q') || '').trim().toLowerCase()
    const tools = state.tools.filter(item => {
      const matchBranch = !branchId || Number(item.branch_id) === Number(branchId)
      const text = `${item.name} ${item.description} ${item.category}`.toLowerCase()
      return matchBranch && (!q || text.includes(q))
    })
    return { tools: tools.map(item => ({ ...item, branch_name: getBranchName(item.branch_id) })) }
  }

  if (rawPath === '/announcements') {
    const branchId = query.get('branchId')
    const announcements = state.announcements.filter(item => !branchId || !item.target_branch_id || Number(item.target_branch_id) === Number(branchId))
    return { announcements }
  }

  if (rawPath === '/books') {
    const q = (query.get('q') || '').trim().toLowerCase()
    const books = state.books.filter(item => !q || `${item.title} ${item.author} ${item.subject}`.toLowerCase().includes(q))
    return { books }
  }

  if (rawPath === '/skills') {
    const q = (query.get('q') || '').trim().toLowerCase()
    const type = query.get('type')
    const skills = state.skills.filter(item => {
      const filteredByQuery = !q || `${item.skill_name} ${item.name} ${item.branch}`.toLowerCase().includes(q)
      const filteredByType = !type || item.type === type
      return filteredByQuery && filteredByType
    })
    return { skills }
  }

  if (rawPath === '/admin/stats') {
    return {
      users: state.users.length,
      notes: state.notes.length,
      books: state.books.length,
      skills: state.skills.length,
      announcements: state.announcements.length
    }
  }

  if (rawPath === '/user/books') {
    const token = getToken()
    if (!token) throw new Error('Login required to list a book.')
    const body = readBody(options)
    const userId = Number(String(token || '').split('-')[2])
    const item = {
      id: Date.now(),
      owner_id: userId,
      title: String(body.title || '').trim(),
      author: String(body.author || '').trim(),
      subject: String(body.subject || '').trim(),
      branch_id: body.branchId ? Number(body.branchId) : null,
      action: ['borrow', 'exchange', 'donate'].includes(body.action) ? body.action : 'borrow',
      location: String(body.location || '').trim(),
      available_until: body.availableUntil || null,
      status: 'available',
      created_at: new Date().toISOString()
    }
    state.books.push(item)
    setDemoState(state)
    return { book: item }
  }

  if (rawPath === '/user/skills') {
    const token = getToken()
    if (!token) throw new Error('Login required to add a skill.')
    const body = readBody(options)
    const userId = Number(String(token || '').split('-')[2])
    const user = state.users.find(item => Number(item.id) === Number(userId))
    const item = {
      id: Date.now(),
      user_id: userId,
      skill_name: String(body.skillName || '').trim(),
      type: ['teach', 'learn'].includes(body.type) ? body.type : 'teach',
      level: body.level || 'beginner',
      name: user?.name || 'Student',
      branch: user ? getBranchName(user.branch_id) : 'General'
    }
    state.skills.push(item)
    setDemoState(state)
    return { skill: item }
  }

  if (rawPath === '/user/book-requests') {
    const token = getToken()
    if (!token) throw new Error('Login required to request a book.')
    const body = readBody(options)
    const userId = Number(String(token || '').split('-')[2])
    const book = state.books.find(item => Number(item.id) === Number(body.bookId))
    if (!book) throw new Error('Book not found')
    if (Number(book.owner_id) === Number(userId)) throw new Error('You cannot request your own book')
    state.bookRequests.push({ id: Date.now(), book_id: Number(body.bookId), requester_id: userId })
    setDemoState(state)
    return { request: { id: Date.now(), book_id: Number(body.bookId), requester_id: userId } }
  }

  if (rawPath === '/admin/notes') {
    const token = getToken()
    if (!token) throw new Error('Not allowed')
    const body = readBody(options)
    const item = {
      id: Date.now(),
      title: String(body.title || '').trim(),
      description: String(body.description || '').trim(),
      subject_id: Number(body.subjectId),
      file_url: '',
      file_name: body.file ? body.file.name : 'demo-note.pdf',
      created_at: new Date().toISOString(),
      subject: state.subjects.find(subject => Number(subject.id) === Number(body.subjectId))?.name || 'General',
      branch: getBranchName(state.subjects.find(subject => Number(subject.id) === Number(body.subjectId))?.branch_id)
    }
    state.notes.unshift(item)
    setDemoState(state)
    return { note: item }
  }

  if (rawPath === '/admin/announcements') {
    const token = getToken()
    if (!token) throw new Error('Not allowed')
    const body = readBody(options)
    const item = {
      id: Date.now(),
      title: String(body.title || '').trim(),
      message: String(body.message || '').trim(),
      target_branch_id: body.targetBranchId ? Number(body.targetBranchId) : null,
      created_at: new Date().toISOString(),
      target_branch: body.targetBranchId ? getBranchName(Number(body.targetBranchId)) : 'All students'
    }
    state.announcements.unshift(item)
    setDemoState(state)
    return { announcement: item }
  }

  throw new Error('Demo endpoint not implemented')
}

export function getToken() { return localStorage.getItem('campushub_token') }
export function getUser() { try { return JSON.parse(localStorage.getItem('campushub_user') || 'null') } catch { return null } }
export function setSession(data) {
  localStorage.setItem('campushub_token', data.token)
  localStorage.setItem('campushub_user', JSON.stringify(data.user))
}
export function clearSession() {
  localStorage.removeItem('campushub_token')
  localStorage.removeItem('campushub_user')
}

export async function api(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')

  let response
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers })
  } catch (error) {
    if (USE_DEMO_FALLBACK && typeof window !== 'undefined') return mockApi(path, options)
    throw error
  }

  const text = await response.text()
  let data = {}
  try { data = text ? JSON.parse(text) : {} } catch { data = { message: text } }
  if (!response.ok) throw new Error(data.message || `Request failed (${response.status})`)
  return data
}
