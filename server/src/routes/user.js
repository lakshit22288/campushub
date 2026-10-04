import { Router } from 'express'
import { pool } from '../db/pool.js'
import { requireAuth } from '../middleware/auth.js'

const router = Router()
router.use(requireAuth)
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

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
    if (typeof skillName !== 'string' || skillName.trim().length > 80) return res.status(400).json({ message: 'Skill name must be 80 characters or fewer' })
    const proficiency = level || 'beginner'
    if (!['beginner','intermediate','advanced'].includes(proficiency)) return res.status(400).json({ message: 'Invalid skill level' })
    const result = await pool.query(
      `INSERT INTO skills(user_id,skill_name,type,level) VALUES($1,$2,$3,$4) RETURNING *`,
      [req.user.id,skillName.trim(),type,proficiency]
    )
    res.status(201).json({ skill: result.rows[0] })
  } catch (err) { next(err) }
})

router.get('/skill-requests', async (req, res, next) => {
  try {
    const { rows } = await pool.query(
      `SELECT sr.id,sr.skill_id,sr.requester_id,s.user_id AS owner_id,s.skill_name,s.level,
              offered.skill_name AS offered_skill_name,sr.message,sr.status,
              sr.requester_completed_at,sr.owner_completed_at,sr.created_at,sr.updated_at,
              my_feedback.id AS my_feedback_id,
              requester.name AS requester_name,rb.name AS requester_branch,
              owner.name AS owner_name,ob.name AS owner_branch,
              CASE WHEN sr.requester_id=$1 THEN 'sent' ELSE 'received' END AS direction
       FROM skill_requests sr
       JOIN skills s ON s.id=sr.skill_id
       JOIN users requester ON requester.id=sr.requester_id
       JOIN users owner ON owner.id=s.user_id
       LEFT JOIN skills offered ON offered.id=sr.offered_skill_id
       LEFT JOIN skill_feedback my_feedback ON my_feedback.request_id=sr.id AND my_feedback.reviewer_id=$1
       LEFT JOIN branches rb ON rb.id=requester.branch_id
       LEFT JOIN branches ob ON ob.id=owner.branch_id
       WHERE sr.requester_id=$1 OR s.user_id=$1
       ORDER BY sr.created_at DESC`,
      [req.user.id]
    )
    res.json({ requests: rows })
  } catch (err) { next(err) }
})

router.post('/skill-requests', async (req, res, next) => {
  try {
    const { skillId, offeredSkillId = null, message = '' } = req.body
    if (typeof skillId !== 'string' || !uuidPattern.test(skillId)) return res.status(400).json({ message: 'A valid skill listing is required' })
    if (typeof message !== 'string' || message.trim().length > 500) return res.status(400).json({ message: 'Request message must be 500 characters or fewer' })
    const skill = await pool.query(`SELECT id,user_id,type FROM skills WHERE id=$1`, [skillId])
    if (!skill.rowCount) return res.status(404).json({ message: 'Skill listing not found' })
    if (skill.rows[0].type !== 'teach') return res.status(400).json({ message: 'You can request a skill that the student is offering to teach' })
    if (skill.rows[0].user_id === req.user.id) return res.status(400).json({ message: 'You cannot request your own skill listing' })
    if (offeredSkillId !== null) {
      if (typeof offeredSkillId !== 'string' || !uuidPattern.test(offeredSkillId)) return res.status(400).json({ message: 'Invalid offered skill listing' })
      const offered = await pool.query(`SELECT id FROM skills WHERE id=$1 AND user_id=$2 AND type='teach'`, [offeredSkillId,req.user.id])
      if (!offered.rowCount) return res.status(400).json({ message: 'Choose one of your own skills you can teach as an exchange offer' })
    }
    const result = await pool.query(
      `INSERT INTO skill_requests(skill_id,requester_id,offered_skill_id,message)
       VALUES($1,$2,$3,$4)
       ON CONFLICT DO NOTHING
       RETURNING id,skill_id,requester_id,offered_skill_id,message,status,created_at`,
      [skillId,req.user.id,offeredSkillId,message.trim()]
    )
    if (!result.rowCount) return res.status(409).json({ message: 'An active request for this skill already exists' })
    res.status(201).json({ request: result.rows[0] })
  } catch (err) { next(err) }
})

router.patch('/skill-requests/:id', async (req, res, next) => {
  try {
    const { id } = req.params
    const { action } = req.body
    if (!uuidPattern.test(id)) return res.status(400).json({ message: 'Invalid request ID' })
    if (!['accept','reject','confirm-completed'].includes(action)) return res.status(400).json({ message: 'Invalid request action' })

    let result
    if (action === 'accept' || action === 'reject') {
      result = await pool.query(
        `UPDATE skill_requests sr
         SET status=$3,updated_at=NOW()
         FROM skills s
         WHERE sr.skill_id=s.id AND sr.id=$1 AND s.user_id=$2 AND sr.status='pending'
         RETURNING sr.id,sr.status,sr.updated_at`,
        [id,req.user.id,action === 'accept' ? 'accepted' : 'rejected']
      )
    } else {
      result = await pool.query(
        `UPDATE skill_requests sr
         SET requester_completed_at=CASE WHEN sr.requester_id=$2 THEN NOW() ELSE sr.requester_completed_at END,
             owner_completed_at=CASE WHEN s.user_id=$2 THEN NOW() ELSE sr.owner_completed_at END,
             status=CASE
               WHEN (sr.requester_id=$2 OR sr.requester_completed_at IS NOT NULL)
                AND (s.user_id=$2 OR sr.owner_completed_at IS NOT NULL) THEN 'completed'
               ELSE sr.status
             END,
             updated_at=NOW()
         FROM skills s
         WHERE sr.skill_id=s.id AND sr.id=$1 AND sr.status='accepted'
           AND (sr.requester_id=$2 OR s.user_id=$2)
         RETURNING sr.id,sr.status,sr.requester_completed_at,sr.owner_completed_at,sr.updated_at`,
        [id,req.user.id]
      )
    }
    if (!result.rowCount) return res.status(409).json({ message: 'This request cannot be changed by your account or is no longer in that state' })
    res.json({ request: result.rows[0] })
  } catch (err) { next(err) }
})

router.post('/skill-requests/:id/feedback', async (req, res, next) => {
  try {
    const { id } = req.params
    const { rating, comment = '' } = req.body
    if (!uuidPattern.test(id)) return res.status(400).json({ message: 'Invalid request ID' })
    if (!Number.isInteger(rating) || rating < 1 || rating > 5) return res.status(400).json({ message: 'Rating must be a whole number from 1 to 5' })
    if (typeof comment !== 'string' || comment.trim().length > 500) return res.status(400).json({ message: 'Feedback must be 500 characters or fewer' })
    const result = await pool.query(
      `INSERT INTO skill_feedback(request_id,reviewer_id,reviewee_id,rating,comment)
       SELECT sr.id,$2,
              CASE WHEN sr.requester_id=$2 THEN s.user_id ELSE sr.requester_id END,
              $3,$4
       FROM skill_requests sr JOIN skills s ON s.id=sr.skill_id
       WHERE sr.id=$1 AND sr.status='completed'
         AND (sr.requester_id=$2 OR s.user_id=$2)
       ON CONFLICT(request_id,reviewer_id) DO NOTHING
       RETURNING id,request_id,reviewer_id,reviewee_id,rating,comment,created_at`,
      [id,req.user.id,rating,comment.trim()]
    )
    if (!result.rowCount) return res.status(409).json({ message: 'Feedback is available once both students confirm completion, once per student' })
    res.status(201).json({ feedback: result.rows[0] })
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
