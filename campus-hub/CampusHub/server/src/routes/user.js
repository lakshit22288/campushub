import { Router } from 'express'
import { pool } from '../db/pool.js'
import { requireAuth } from '../middleware/auth.js'

const router = Router()
router.use(requireAuth)

router.post('/books', async (req, res, next) => {
  try {
    const { title, author, subject, branchId, action, location, availableUntil } = req.body
    if (!title) return res.status(400).json({ message: 'Title is required' })
    if (!['borrow','exchange','donate'].includes(action || 'borrow')) return res.status(400).json({ message: 'Invalid action' })
    const result = await pool.query(
      `INSERT INTO books(owner_id,title,author,subject,branch_id,action,location,available_until)
       VALUES($1,$2,$3,$4,$5,$6,$7,$8) RETURNING *`,
      [req.user.id,title.trim(),author||'',subject||'',branchId||null,action||'borrow',location||'',availableUntil||null]
    )
    res.status(201).json({ book: result.rows[0] })
  } catch (err) { next(err) }
})

router.post('/skills', async (req, res, next) => {
  try {
    const { skillName, type, level } = req.body
    if (!skillName || !['teach','learn'].includes(type)) return res.status(400).json({ message: 'Skill and valid type are required' })
    const result = await pool.query(
      `INSERT INTO skills(user_id,skill_name,type,level) VALUES($1,$2,$3,$4) RETURNING *`,
      [req.user.id,skillName.trim(),type,level||'beginner']
    )
    res.status(201).json({ skill: result.rows[0] })
  } catch (err) { next(err) }
})

router.post('/book-requests', async (req, res, next) => {
  try {
    const { bookId } = req.body
    if (!bookId) return res.status(400).json({ message: 'bookId is required' })
    const book = await pool.query(`SELECT id,owner_id,status FROM books WHERE id=$1`, [bookId])
    if (!book.rowCount) return res.status(404).json({ message: 'Book not found' })
    if (book.rows[0].owner_id === req.user.id) return res.status(400).json({ message: 'You cannot request your own book' })
    if (book.rows[0].status !== 'available') return res.status(409).json({ message: 'This book is not currently available' })
    const result = await pool.query(
      `INSERT INTO book_requests(book_id,requester_id) VALUES($1,$2)
       ON CONFLICT(book_id,requester_id) DO NOTHING RETURNING *`,
      [bookId,req.user.id]
    )
    if (!result.rowCount) return res.status(409).json({ message: 'Request already exists' })
    await pool.query(`UPDATE books SET status='requested' WHERE id=$1 AND status='available'`, [bookId])
    res.status(201).json({ request: result.rows[0] })
  } catch (err) { next(err) }
})

export default router
