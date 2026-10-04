import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = supabaseUrl && supabaseKey
  ? createClient(supabaseUrl, supabaseKey, {
      auth: {
        autoRefreshToken: false,
        detectSessionInUrl: true,
        persistSession: true
      }
    })
  : null

export async function signInWithGoogle() {
  if (!supabase) {
    throw new Error('Google sign-in is not configured yet. Add the Supabase URL and publishable key to client/.env.')
  }

  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: `${window.location.origin}/auth/callback` }
  })

  if (error) throw error
}
