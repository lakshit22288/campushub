import { Router } from 'express'
import bcrypt from 'bcryptjs'
import { pool } from '../db/pool.js'
import { makeToken } from '../utils/auth.js'
import { requireAuth } from '../middleware/auth.js'

const router = Router()

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
