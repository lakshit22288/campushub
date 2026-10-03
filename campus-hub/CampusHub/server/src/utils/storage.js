import fs from 'fs/promises'
import path from 'path'
import { createClient } from '@supabase/supabase-js'

let client = null
if (process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY) {
  client = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, {
    auth: { persistSession: false, autoRefreshToken: false }
  })
}

export async function saveUploadedFile(file) {
  if (!file) return { url: null, fileName: null }

  if (client) {
    const bucket = process.env.SUPABASE_STORAGE_BUCKET || 'campushub-files'
    const ext = path.extname(file.originalname || '').toLowerCase() || '.bin'
    const objectPath = `notes/${Date.now()}-${Math.random().toString(36).slice(2)}${ext}`
    const data = await fs.readFile(file.path)
    const { error } = await client.storage.from(bucket).upload(objectPath, data, {
      contentType: file.mimetype,
      upsert: false
    })
    if (error) throw new Error(`Storage upload failed: ${error.message}`)
    const { data: publicData } = client.storage.from(bucket).getPublicUrl(objectPath)
    await fs.unlink(file.path).catch(() => {})
    return { url: publicData.publicUrl, fileName: file.originalname }
  }

  if (process.env.NODE_ENV === 'production') {
    throw new Error('Production file storage is not configured. Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and SUPABASE_STORAGE_BUCKET.')
  }

  return { url: `/uploads/${path.basename(file.path)}`, fileName: file.originalname }
}
