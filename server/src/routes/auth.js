import { Router } from 'express'
import bcrypt from 'bcryptjs'
import { randomBytes } from 'node:crypto'
import { createClient } from '@supabase/supabase-js'
import { pool } from '../db/pool.js'
import { makeToken } from '../utils/auth.js'
import { requireAuth } from '../middleware/auth.js'

const router = Router()
let supabaseAuth

function getSupabaseAuth() {
  const { SUPABASE_URL, SUPABASE_ANON_KEY } = process.env
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) return null
  if (!supabaseAuth) supabaseAuth = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: { autoRefreshToken: false, persistSession: false }
  })
  return supabaseAuth
}

function createAppSession(user, res, status = 200) {
  return res.status(status).json({ token: makeToken(user), user })
}

router.post('/register', async (req, res, next) => {
  try {
    const { name, email, password, branchId, semester } = req.body
    if (!name || !email || !password) return res.status(400).json({ message: 'Name, email and password are required' })
    if (password.length < 6) return res.status(400).json({ message: 'Password must be at least 6 characters' })

    const existing = await pool.query('SELECT id FROM users WHERE LOWER(email)=LOWER($1)', [email])
    if (existing.rowCount) return res.status(409).json({ message: 'Email already registered' })

    const passwordHash = await bcrypt.hash(password, 12)
    const result = await pool.query(
      `INSERT INTO users (name,email,password_hash,branch_id,semester)
       VALUES ($1,$2,$3,$4,$5)
       RETURNING id,name,email,role,branch_id,semester`,
      [name.trim(), email.trim().toLowerCase(), passwordHash, branchId || null, semester || null]
    )
    const user = result.rows[0]
    res.status(201).json({ token: makeToken(user), user })
  } catch (err) { next(err) }
})

router.post('/login', async (req, res, next) => {
  try {
    const { email, password } = req.body
    if (!email || !password) return res.status(400).json({ message: 'Email and password are required' })

    const result = await pool.query(
      `SELECT id,name,email,password_hash,role,branch_id,semester,bio FROM users WHERE LOWER(email)=LOWER($1)`,
      [email.trim()]
    )
    if (!result.rowCount) return res.status(401).json({ message: 'Invalid email or password' })

    const user = result.rows[0]
    const ok = await bcrypt.compare(password, user.password_hash)
    if (!ok) return res.status(401).json({ message: 'Invalid email or password' })

    delete user.password_hash
    res.json({ token: makeToken(user), user })
  } catch (err) { next(err) }
})

router.post('/google', async (req, res, next) => {
  try {
    const client = getSupabaseAuth()
    if (!client) return res.status(503).json({ message: 'Google sign-in is not configured on the server.' })

    const { accessToken, branchId, semester } = req.body
    if (typeof accessToken !== 'string' || !accessToken) {
      return res.status(400).json({ message: 'A Google sign-in token is required.' })
    }

    const { data, error } = await client.auth.getUser(accessToken)
    const identity = data?.user
    const usedGoogleProvider = identity?.app_metadata?.provider === 'google'
      || identity?.identities?.some(item => item.provider === 'google')
    if (error || !identity || !usedGoogleProvider || !identity.email || !identity.email_confirmed_at) {
      return res.status(401).json({ message: 'Google could not verify this account. Please try again.' })
    }

    const email = identity.email.trim().toLowerCase()
    const existing = await pool.query(
      `SELECT id,name,email,role,branch_id,semester,bio
       FROM users WHERE LOWER(email)=LOWER($1)`,
      [email]
    )
    if (existing.rowCount) return createAppSession(existing.rows[0], res)

    if (!branchId) return res.json({ profileRequired: true })

    const branch = await pool.query('SELECT id FROM branches WHERE id=$1', [branchId])
    if (!branch.rowCount) return res.status(400).json({ message: 'Choose a valid branch.' })

    const parsedSemester = semester === null || semester === undefined || semester === ''
      ? null
      : Number(semester)
    if (parsedSemester !== null && (!Number.isInteger(parsedSemester) || parsedSemester < 1 || parsedSemester > 12)) {
      return res.status(400).json({ message: 'Semester must be a number from 1 to 12.' })
    }

    const name = String(identity.user_metadata?.full_name || identity.user_metadata?.name || email.split('@')[0]).trim()
    const unusablePasswordHash = await bcrypt.hash(randomBytes(48).toString('hex'), 12)
    let created
    try {
      created = await pool.query(
        `INSERT INTO users (name,email,password_hash,branch_id,semester)
         VALUES ($1,$2,$3,$4,$5)
         RETURNING id,name,email,role,branch_id,semester,bio`,
        [name || email.split('@')[0], email, unusablePasswordHash, branchId, parsedSemester]
      )
    } catch (insertError) {
      if (insertError.code !== '23505') throw insertError
      const raced = await pool.query(
        `SELECT id,name,email,role,branch_id,semester,bio
         FROM users WHERE LOWER(email)=LOWER($1)`,
        [email]
      )
      if (!raced.rowCount) throw insertError
      return createAppSession(raced.rows[0], res)
    }

    return createAppSession(created.rows[0], res, 201)
  } catch (err) { next(err) }
})

router.get('/me', requireAuth, async (req, res, next) => {
  try {
    const result = await pool.query(
      `SELECT u.id,u.name,u.email,u.role,u.branch_id,u.semester,u.bio,b.name AS branch_name
       FROM users u LEFT JOIN branches b ON b.id=u.branch_id WHERE u.id=$1`,
      [req.user.id]
    )
    if (!result.rowCount) return res.status(404).json({ message: 'User not found' })
    res.json({ user: result.rows[0] })
  } catch (err) { next(err) }
})

export default router
