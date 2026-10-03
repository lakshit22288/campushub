import pg from 'pg'
import dotenv from 'dotenv'

dotenv.config()

const { Pool } = pg
const databaseHost = process.env.DATABASE_URL
  ? new URL(process.env.DATABASE_URL).hostname
  : ''
const useSsl = process.env.NODE_ENV === 'production'
  || databaseHost.endsWith('.pooler.supabase.com')
  || databaseHost.endsWith('.supabase.co')

export const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: useSsl ? { rejectUnauthorized: false } : false,
  max: Number(process.env.DB_POOL_MAX || 10)
})

pool.on('error', (err) => {
  console.error('Unexpected PostgreSQL pool error:', err)
})
