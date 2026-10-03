import { Router } from 'express'
import { pool } from '../db/pool.js'

const router = Router()

router.get('/branches', async (_req, res, next) => {
  try {
    const { rows } = await pool.query('SELECT id,name,code,icon FROM branches ORDER BY name')
    res.json({ branches: rows })
  } catch (err) { next(err) }
})

router.get('/subjects', async (req, res, next) => {
  try {
    const { branchId } = req.query
    const params = []
    let sql = `SELECT s.id,s.name,s.slug,b.name AS branch_name,b.code FROM subjects s JOIN branches b ON b.id=s.branch_id`
    if (branchId) { params.push(branchId); sql += ' WHERE s.branch_id=$1' }
    sql += ' ORDER BY s.name'
    const { rows } = await pool.query(sql, params)
    res.json({ subjects: rows })
  } catch (err) { next(err) }
})

router.get('/notes', async (req, res, next) => {
  try {
    const { branchId, subjectId, q } = req.query
    const params = []
    const filters = []
    if (branchId) { params.push(branchId); filters.push(`s.branch_id=$${params.length}`) }
    if (subjectId) { params.push(subjectId); filters.push(`n.subject_id=$${params.length}`) }
    if (q) { params.push(`%${q}%`); filters.push(`(n.title ILIKE $${params.length} OR n.description ILIKE $${params.length})`) }
    let sql = `SELECT n.id,n.title,n.description,n.file_url,n.file_name,n.created_at,s.name AS subject,b.name AS branch
               FROM notes n JOIN subjects s ON s.id=n.subject_id JOIN branches b ON b.id=s.branch_id`
    if (filters.length) sql += ` WHERE ${filters.join(' AND ')}`
    sql += ' ORDER BY n.created_at DESC LIMIT 100'
    const { rows } = await pool.query(sql, params)
    res.json({ notes: rows })
  } catch (err) { next(err) }
})

router.get('/tools', async (req, res, next) => {
  try {
    const { branchId, q } = req.query
    const params = []
    const filters = []
    if (branchId) { params.push(branchId); filters.push(`t.branch_id=$${params.length}`) }
    if (q) { params.push(`%${q}%`); filters.push(`(t.name ILIKE $${params.length} OR t.description ILIKE $${params.length} OR t.category ILIKE $${params.length})`) }
    let sql = `SELECT t.*,b.name AS branch_name,s.name AS subject_name FROM tools t
               LEFT JOIN branches b ON b.id=t.branch_id LEFT JOIN subjects s ON s.id=t.subject_id`
    if (filters.length) sql += ` WHERE ${filters.join(' AND ')}`
    sql += ' ORDER BY t.name'
    const { rows } = await pool.query(sql, params)
    res.json({ tools: rows })
  } catch (err) { next(err) }
})

router.get('/announcements', async (req, res, next) => {
  try {
    const { branchId } = req.query
    const params = []
    let sql = `SELECT a.id,a.title,a.message,a.created_at,b.name AS target_branch
               FROM announcements a LEFT JOIN branches b ON b.id=a.target_branch_id`
    if (branchId) { params.push(branchId); sql += ' WHERE a.target_branch_id IS NULL OR a.target_branch_id=$1' }
    sql += ' ORDER BY a.created_at DESC LIMIT 30'
    const { rows } = await pool.query(sql, params)
    res.json({ announcements: rows })
  } catch (err) { next(err) }
})

router.get('/books', async (req, res, next) => {
  try {
    const { q, branchId } = req.query
    const params = []
    const filters = [`bo.status <> 'closed'`]
    if (q) { params.push(`%${q}%`); filters.push(`(bo.title ILIKE $${params.length} OR bo.author ILIKE $${params.length} OR bo.subject ILIKE $${params.length})`) }
    if (branchId) { params.push(branchId); filters.push(`bo.branch_id=$${params.length}`) }
    const sql = `SELECT bo.id,bo.title,bo.author,bo.subject,bo.action,bo.location,bo.available_until,bo.status,
                        u.name AS owner_name,b.name AS branch_name
                 FROM books bo JOIN users u ON u.id=bo.owner_id LEFT JOIN branches b ON b.id=bo.branch_id
                 WHERE ${filters.join(' AND ')} ORDER BY bo.created_at DESC LIMIT 100`
    const { rows } = await pool.query(sql, params)
    res.json({ books: rows })
  } catch (err) { next(err) }
})

router.get('/skills', async (req, res, next) => {
  try {
    const { q, type } = req.query
    const params = []
    const filters = []
    if (q) { params.push(`%${q}%`); filters.push(`s.skill_name ILIKE $${params.length}`) }
    if (type) { params.push(type); filters.push(`s.type=$${params.length}`) }
    let sql = `SELECT s.id,s.skill_name,s.type,s.level,u.id AS user_id,u.name,u.bio,b.name AS branch
               FROM skills s JOIN users u ON u.id=s.user_id LEFT JOIN branches b ON b.id=u.branch_id`
    if (filters.length) sql += ` WHERE ${filters.join(' AND ')}`
    sql += ' ORDER BY s.created_at DESC LIMIT 100'
    const { rows } = await pool.query(sql, params)
    res.json({ skills: rows })
  } catch (err) { next(err) }
})

export default router
