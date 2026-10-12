# CampusHub Python edition

The Django app is the maintained CampusHub application, deployed at `https://campushub-python.vercel.app` from the `python_app` Vercel project root. The legacy `https://campushub-opal.vercel.app` domain remains a compatibility alias that forwards to the Python Render production service. The app uses Supabase PostgreSQL through unmanaged models; do not run Django migrations against that database.

## Staging deployment

The repository's Render Blueprint defines a separate `campushub-python-staging` web service with automatic deploys disabled. Review the Blueprint in Render, then set the staging service's `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` to an **isolated staging Supabase project**, not production. Create `campushub-staging-files` as a **private** Storage bucket. Django stores object paths and creates one-hour signed download URLs; branch-targeted notice attachments are signed only for the target branch or admins. Add the additive SQL scripts for the note source type, project attachments, and notice attachments to the staging database before deploying. Render generates a unique Django secret key; the service uses WhiteNoise for collected static assets and Gunicorn to serve Django. HTTPS redirects, secure cookies, and one-hour HSTS are enabled for the staging host.

The default staging origin is `https://campushub-python-staging.onrender.com`. If Render assigns another hostname, update `DJANGO_PUBLIC_URL`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS` together. Add `https://campushub-python-staging.onrender.com/auth/callback` to the staging Supabase Auth allowed redirect URLs. Do not change the production Supabase Site URL or production OAuth callback during staging.

Staging remains isolated verification only and must never write to production data. Signed download URLs are bearer links and remain usable until they expire; do not publish them in logs or share them outside the intended audience.

## Production deployment

The Render Blueprint defines a `campushub-python-production` compatibility service with automatic deploys disabled. The old Vercel alias proxies to this service; the maintained Vercel project deploys the Django app directly from the `python_app` root. Render releases are deployed manually from `main`.

Configure the production service with the existing production Supabase PostgreSQL connection string, Supabase URL and publishable key, plus the server-only legacy `service_role` JWT required by the storage helper. Keep `SUPABASE_STORAGE_BUCKET` set to the existing `campushub-files` bucket so existing public file references continue to work. That bucket is public, so configure a separate private `campushub-python-files` bucket as `SUPABASE_UPLOAD_BUCKET`; new Python uploads are stored there with bucket-qualified references, while pre-existing public references continue to resolve through the legacy bucket. Do not make the existing bucket private or use staging credentials. Set `DJANGO_PUBLIC_URL` to the exact production-facing origin, `DJANGO_ALLOWED_HOSTS` to the exact Render and Vercel hostnames, and `DJANGO_CSRF_TRUSTED_ORIGINS` to the HTTPS production origin. Keep all secrets in Render environment settings.

The production health endpoint, database connection, Google OAuth provider redirect, and private bucket upload/signed-download path have been smoke-tested. Complete an account-based sign-in and authenticated workflow acceptance test after deployment; do not create test accounts or write sample records to the production database. Retain the legacy Vercel alias and Render compatibility service unless they are deliberately retired.

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

The settings load `python_app/.env` and retain a fallback to an already-existing ignored `server/.env` for local backward compatibility; new setups should use `python_app/.env`. `DATABASE_URL` should use the existing Supabase PostgreSQL connection string. Never commit either environment file or share its contents in chat. When no database URL is configured in development, the app falls back to local SQLite for UI work.

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

All mapped Supabase models are unmanaged; do not run Django migrations against the existing database. Other than the explicitly approved additive note, project, and announcement fields documented below, do not create or alter production tables.

The approved teacher/AI resource split adds one `source_type` discriminator to the existing `notes` table. This additive migration has been applied to the configured Supabase database; for another environment, run `sql/add_note_source_type.sql` once before deploying code that reads this field. Existing uploads keep the default `teacher` category. The baseline `sql/schema.sql` includes the field for fresh databases.

Campus notice attachments add nullable `attachment_url` and `attachment_name` fields to the existing `announcements` table. This additive migration has been applied to the configured Supabase database; run `sql/add_announcement_attachments.sql` once in other environments before publishing a notice with an attachment. The baseline schema includes both fields for fresh databases. Only admins and super-admins are offered the optional PDF/PNG/JPG upload.

The Django app filters study-resource search and BranchHub navigation to a signed-in non-admin account's assigned branch, and subject resource pages require a signed-in account from that branch (admins can access all branches). In the Python app, notes and attachments are stored in a private Supabase Storage bucket; signed links are generated only when the corresponding authorized page is rendered and expire after one hour.

Student project attachments add nullable `attachment_url` and `attachment_name` fields to the existing `projects` table. This additive migration has been applied to the configured Supabase database; run `sql/add_project_attachments.sql` once in other environments before using this upload feature. The baseline schema includes both fields for new databases. Attachments are optional and are limited to ZIP/PDF/PNG/JPG files up to 10 MB.

Google OAuth uses Supabase's callback. For local testing, add `http://127.0.0.1:8000/auth/callback` to Supabase Auth's allowed redirects; retain the current Site URL and existing callback URLs. Configure `DJANGO_PUBLIC_URL` only for an intended Django deployment. Keep the Supabase service-role key server-side; it is used only by the Storage upload helper.
