import { Router } from 'express'
import multer from 'multer'
import path from 'path'
import { pool } from '../db/pool.js'
import { requireAuth, requireRole } from '../middleware/auth.js'
import { saveUploadedFile } from '../utils/storage.js'

const router = Router()
router.use(requireAuth, requireRole('admin','super_admin','teacher','moderator'))

const upload = multer({
  dest: 'uploads/',
  limits: { fileSize: 10 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const ok = ['application/pdf','image/png','image/jpeg'].includes(file.mimetype)
    cb(ok ? null : new Error('Only PDF, PNG and JPG files are allowed'), ok)
  }
})

function canManageContent(role) { return ['admin','super_admin','teacher'].includes(role) }

router.get('/stats', async (_req, res, next) => {
  try {
    const queries = await Promise.all([
      pool.query('SELECT COUNT(*)::int AS count FROM users'),
      pool.query('SELECT COUNT(*)::int AS count FROM notes'),
      pool.query('SELECT COUNT(*)::int AS count FROM books'),
      pool.query('SELECT COUNT(*)::int AS count FROM skills'),
      pool.query('SELECT COUNT(*)::int AS count FROM announcements')
    ])
    res.json({
      users: queries[0].rows[0].count,
      notes: queries[1].rows[0].count,
      books: queries[2].rows[0].count,
      skills: queries[3].rows[0].count,
      announcements: queries[4].rows[0].count
    })
  } catch (err) { next(err) }
})

router.post('/notes', upload.single('file'), async (req, res, next) => {
  try {
    if (!canManageContent(req.user.role)) return res.status(403).json({ message: 'Not allowed' })
    const { title, description, subjectId } = req.body
    if (!title || !subjectId) return res.status(400).json({ message: 'Title and subject are required' })
    const uploaded = await saveUploadedFile(req.file)
    const result = await pool.query(
      `INSERT INTO notes(title,description,subject_id,file_url,file_name,created_by)
       VALUES($1,$2,$3,$4,$5,$6) RETURNING *`,
      [title.trim(), description || '', subjectId, uploaded.url, uploaded.fileName, req.user.id]
    )
    res.status(201).json({ note: result.rows[0] })
  } catch (err) { next(err) }
})

router.post('/announcements', async (req, res, next) => {
  try {
    if (!canManageContent(req.user.role)) return res.status(403).json({ message: 'Not allowed' })
    const { title, message, targetBranchId } = req.body
    if (!title || !message) return res.status(400).json({ message: 'Title and message are required' })
    const result = await pool.query(
      `INSERT INTO announcements(title,message,target_branch_id,created_by) VALUES($1,$2,$3,$4) RETURNING *`,
      [title.trim(), message.trim(), targetBranchId || null, req.user.id]
    )
    res.status(201).json({ announcement: result.rows[0] })
  } catch (err) { next(err) }
})

export default router
