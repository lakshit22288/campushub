# CampusHub

Everything you need for college, all in one place.

CampusHub is a college student platform for learning, sharing resources, finding project ideas, and running code.

## Deploy to Vercel

CampusHub uses separate Vercel projects for the frontend and the Express API. Both projects can use the same GitHub repository.

### Frontend

Create/import a Vercel project with the repository root directory set to `client` and the Vite framework preset. Configure these Production environment variables:

- `VITE_SUPABASE_URL`: the Supabase project URL.
- `VITE_SUPABASE_ANON_KEY`: the Supabase publishable key (never the secret/service-role key).
- `VITE_API_URL`: add after deploying the API; use the API project's origin followed by `/api`.

### API

Create a second Vercel project from the same repository with the root directory set to `server` and the Express framework preset. Vercel detects `src/server.js` as the Express entry point.

Configure these Production environment variables:

- `CLIENT_URL`: the exact deployed frontend origin, such as `https://campushub.vercel.app`.
- `DATABASE_URL`: the existing Supabase Postgres connection string. Use Supabase's Session Pooler connection details; do not create or migrate a separate database for deployment.
- `DB_POOL_MAX`: `1` to keep serverless database connections bounded.
- `JWT_SECRET`: a new, long, random secret.
- `SUPABASE_URL`: the Supabase project URL.
- `SUPABASE_ANON_KEY`: the Supabase publishable key, used to verify Supabase Auth tokens.
- `SUPABASE_SERVICE_ROLE_KEY`: optional; configure only if the API needs to upload files to Supabase Storage. Keep it server-side.
- `SUPABASE_STORAGE_BUCKET`: the existing Storage bucket name, when file uploads are enabled.

After the API deploys, set the frontend's `VITE_API_URL` to `https://<api-project>.vercel.app/api` and redeploy the frontend. In Supabase Authentication URL Configuration, set the Site URL to the frontend origin and add `https://<frontend-project>.vercel.app/auth/callback` to the allowed redirect URLs.

Do not add `.env` files, database URLs, JWT secrets, or Supabase secret/service-role keys to GitHub or frontend environment variables. Vercel's free-plan function limits and provider availability may affect usage; the API's compiler proxy also depends on OneCompiler. Python's interactive runner executes in the user's browser using Pyodide.
