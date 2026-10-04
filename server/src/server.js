import express from 'express'
import cors from 'cors'
import morgan from 'morgan'
import dotenv from 'dotenv'
import path from 'path'
import { fileURLToPath } from 'url'
import authRoutes from './routes/auth.js'
import publicRoutes from './routes/public.js'
import adminRoutes from './routes/admin.js'
import userRoutes from './routes/user.js'
import compilerRoutes from './routes/compiler.js'
import { pool } from './db/pool.js'

dotenv.config()
const app = express()
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const allowedOrigins = new Set([
  'https://campushub-opal.vercel.app',
  ...(process.env.CLIENT_URL || 'http://localhost:5173')
    .split(',')
    .map(v => v.trim().replace(/\/+$/, ''))
])
app.use(cors({ origin: (origin, callback) => {
  const localDevelopmentOrigin = process.env.NODE_ENV !== 'production'
    && /^http:\/\/(localhost|127\.0\.0\.1):\d+$/.test(origin || '')
  if (!origin || allowedOrigins.has(origin) || localDevelopmentOrigin) return callback(null, true)
  return callback(new Error('CORS blocked'))
} }))
app.use(express.json({ limit: '1mb' }))
app.use(express.urlencoded({ extended: true }))
app.use(morgan('dev'))
if (!process.env.VERCEL) {
  app.use('/uploads', express.static(path.join(__dirname, '../../uploads')))
}

app.get('/api/health', async (_req, res) => {
  try {
    await pool.query('SELECT 1')
    res.json({ ok: true, service: 'CampusHub API', database: 'connected' })
  } catch {
    res.status(503).json({ ok: false, service: 'CampusHub API', database: 'disconnected' })
  }
})

app.use('/api/auth', authRoutes)
app.use('/api', publicRoutes)
app.use('/api/admin', adminRoutes)
app.use('/api/user', userRoutes)
app.use('/api/compiler', compilerRoutes)

app.use((err, _req, res, _next) => {
  console.error(err)
  const message = err.code === 'LIMIT_FILE_SIZE' ? 'File too large (max 10MB)' : (err.message || 'Internal server error')
  res.status(500).json({ message })
})

const port = Number(process.env.PORT || 5000)
if (!process.env.VERCEL) {
  app.listen(port, () => console.log(`CampusHub API running on http://localhost:${port}`))
}

export default app
