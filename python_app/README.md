# CampusHub Python edition

The Django app is a side-by-side staging service, not yet a replacement for the live React/Express deployment. It uses Supabase PostgreSQL through unmanaged models; do not run Django migrations against that database.

## Staging deployment

The repository's Render Blueprint defines a separate `campushub-python-staging` web service with automatic deploys disabled. It leaves the existing Node API and Vercel frontend untouched. Review the Blueprint in Render, then set the staging service's `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` to an **isolated staging Supabase project**, not production. Create `campushub-staging-files` as a **private** Storage bucket. Django stores object paths and creates one-hour signed download URLs; branch-targeted notice attachments are signed only for the target branch or admins. Add the additive SQL scripts for the note source type, project attachments, and notice attachments to the staging database before deploying. Render generates a unique Django secret key; the service uses WhiteNoise for collected static assets and Gunicorn to serve Django. HTTPS redirects, secure cookies, and one-hour HSTS are enabled for the staging host.

The default staging origin is `https://campushub-python-staging.onrender.com`. If Render assigns another hostname, update `DJANGO_PUBLIC_URL`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS` together. Add `https://campushub-python-staging.onrender.com/auth/callback` to the staging Supabase Auth allowed redirect URLs. Do not change the production Supabase Site URL or production OAuth callback during staging.

Staging is for isolated verification only. Do not switch production traffic until authentication, OAuth, database writes, real file uploads, all primary workflows, and production security/storage requirements have been verified. Signed download URLs are bearer links and remain usable until they expire; do not publish them in logs or share them outside the intended audience. The existing React/Express production app and its Storage configuration are unchanged.

## Production cutover preparation

The Render Blueprint also defines a separate `campushub-python-production` service with automatic deploys disabled. It is intentionally not connected to production by default. Keep the existing Vercel and Express deployments serving users until the production service is configured and validated.

Configure the production service with the existing production Supabase PostgreSQL connection string, Supabase URL and publishable key, plus the server-only legacy `service_role` JWT required by the storage helper. Keep `SUPABASE_STORAGE_BUCKET` set to the existing `campushub-files` bucket so existing public file references continue to work. That bucket is public, so configure a separate private `campushub-python-files` bucket as `SUPABASE_UPLOAD_BUCKET`; new Python uploads are stored there with bucket-qualified references, while pre-existing public references continue to resolve through the legacy bucket. Do not make the existing bucket private or use staging credentials. Set `DJANGO_PUBLIC_URL` to the exact production-facing origin, `DJANGO_ALLOWED_HOSTS` to the exact Render and Vercel hostnames, and `DJANGO_CSRF_TRUSTED_ORIGINS` to the HTTPS production origin. Keep all secrets in Render environment settings.

Before switching Vercel traffic, verify production schema compatibility without running Django migrations, confirm the storage bucket is private or migrate existing files and references to a private bucket, allow the production `/auth/callback` URL in Supabase Auth, then test login, registration, Google sign-in, branch authorization, uploads/downloads, and primary workflows against the production service. Only after those checks pass should Vercel be configured to proxy the production origin; verify the Vercel URL end to end and retain the previous Vercel deployment for rollback. A Render service definition alone does not create the Vercel proxy or perform a traffic cutover.

## Local setup

From the repository root in PowerShell:

```powershell
py -3.14 -m venv python_app\.venv
python_app\.venv\Scripts\Activate.ps1
python -m pip install -r python_app\requirements.txt
if (!(Test-Path python_app\.env)) { Copy-Item python_app\.env.example python_app\.env }
python python_app\manage.py check
python python_app\manage.py runserver 127.0.0.1:8000
```

The settings load `python_app/.env` first and then the existing ignored `server/.env`. `DATABASE_URL` should use the existing Supabase PostgreSQL connection string. Never commit either environment file or share its contents in chat. When no database URL is configured in development, the app falls back to local SQLite for UI work.

Open `http://127.0.0.1:8000/`; check connectivity at `/health/`. Run focused verification with:

```powershell
python_app\.venv\Scripts\python.exe python_app\manage.py check
python_app\.venv\Scripts\python.exe python_app\manage.py test portal --verbosity 2
```

## Current Python features

- Campus home, branch directory, BranchHub subjects/resources/tools, and cross-campus search.
- Branch-scoped study resources: signed-in students and branch teacher accounts are limited to their assigned branch; teacher uploads display the branch identity.
- Student calculators and study utilities: percentage, CGPA, general/mechanical unit conversions, Python concept practice, SQL formatting (never executed), Linux command reference, IPv4 subnetting, Ohm's law, power, logic gates, area/volume, and dilution calculations.
- A restored 10-language Code Lab: Python executes in a browser Web Worker with interactive `input()` and time/output bounds; nine languages use the OneCompiler cloud API.
- Email/password sign-in with bcrypt-compatible hashes, Supabase Google OAuth using PKCE, and student profile editing.
- BookShare listings and request/accept/reject/return flows.
- SkillSwap teach/learn listings, reciprocal requests, two-sided completion, and feedback.
- Help requests and owner resolution, a project idea catalog/submissions, and staff content/role administration.
- PDF/PNG/JPG academic-resource and campus-notice uploads plus ZIP/PDF/PNG/JPG student project attachments to Supabase Storage (10 MB maximum; MIME/extension and file-signature checks).

The existing Code Lab route/shell is intentionally kept separate and is not redesigned. Python Code Lab execution was verified in a local browser; the nine OneCompiler-backed languages are mocked in unit tests and have not been run against the external service. Code and stdin for those nine languages are sent to OneCompiler, so the UI warns users not to include private data. The Python Basics Practice utility is a fixed concept quiz and never executes arbitrary code. Features requiring tables absent from the existing schema (for example help replies, quizzes/practicals, team memberships, reports, and notifications) are not claimed as implemented. Database writes, live OAuth, and real Storage uploads still require isolated end-to-end verification.

## Existing database and deployment safety

All mapped Supabase models are unmanaged; do not run Django migrations against the existing database. Other than the explicitly approved additive note, project, and announcement fields documented below, do not create or alter production tables. Local development and staging do not change the React/Express deployment, production Supabase Auth settings, or Vercel projects. Do not cut over production without explicit readiness review.

The approved teacher/AI resource split adds one `source_type` discriminator to the existing `notes` table. This additive migration has been applied to the configured Supabase database; for another environment, run `server/src/db/add_note_source_type.sql` once before deploying code that reads this field. Existing and legacy uploads keep the default `teacher` category; new React/Express inserts also use that default. The baseline `server/src/db/schema.sql` includes the field for fresh databases.

Campus notice attachments add nullable `attachment_url` and `attachment_name` fields to the existing `announcements` table. This additive migration has been applied to the configured Supabase database; run `server/src/db/add_announcement_attachments.sql` once in other environments before publishing a notice with an attachment. The baseline schema includes both fields for fresh databases. Only admins and super-admins are offered the optional PDF/PNG/JPG upload.

The Django app filters study-resource search and BranchHub navigation to a signed-in non-admin account's assigned branch, and subject resource pages require a signed-in account from that branch (admins can access all branches). In the Python app, notes and attachments are stored in a private Supabase Storage bucket; signed links are generated only when the corresponding authorized page is rendered and expire after one hour.

Student project attachments add nullable `attachment_url` and `attachment_name` fields to the existing `projects` table. This additive migration has been applied to the configured Supabase database; run `server/src/db/add_project_attachments.sql` once in other environments before using this upload feature. The baseline schema includes both fields for new databases. Attachments are optional and are limited to ZIP/PDF/PNG/JPG files up to 10 MB.

Google OAuth uses Supabase's callback. For local testing, add `http://127.0.0.1:8000/auth/callback` to Supabase Auth's allowed redirects; retain the current Site URL and React production callback. Configure `DJANGO_PUBLIC_URL` only for an intended Django deployment. Keep the Supabase service-role key server-side; it is used only by the Storage upload helper.
