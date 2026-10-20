# CampuZHub Python edition

The Django app is the maintained CampuZHub application, deployed at `https://campushub-python.vercel.app` from the `python_app` Vercel project root. The public website address is unchanged by the CampuZHub branding. The Vercel Function is pinned to `bom1` (Mumbai), near the production Supabase database region, to avoid cross-continent database round trips. The legacy `https://campushub-opal.vercel.app` domain remains a compatibility alias that forwards to the Python Render production service. The app uses Supabase PostgreSQL through unmanaged models; do not run Django migrations against that database.

## Google Search visibility

The app publishes a crawlable `robots.txt` and `sitemap.xml`, canonical URLs for `campushub-python.vercel.app`, descriptive page metadata, and marks account-only pages `noindex`. After a successful production deployment, add the URL-prefix property `https://campushub-python.vercel.app/` in [Google Search Console](https://search.google.com/search-console), complete Google's ownership verification, and submit `https://campushub-python.vercel.app/sitemap.xml`. Google decides when to crawl and index pages; submission is not a guarantee of indexing or ranking. A custom domain is recommended if CampuZHub gets one, because the current address is a shared `vercel.app` subdomain.

## Staging deployment

The repository's Render Blueprint defines a separate `campushub-python-staging` web service with automatic deploys disabled. Review the Blueprint in Render, then set the staging service's `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` to an **isolated staging Supabase project**, not production. Create `campushub-staging-files` as a **private** Storage bucket. Django stores object paths and creates one-hour signed download URLs; branch-targeted notice attachments are signed only for the target branch or admins. Add the additive SQL scripts for the note source type, project attachments, and notice attachments to the staging database before deploying. Render generates a unique Django secret key; the service uses WhiteNoise for collected static assets and Gunicorn to serve Django. HTTPS redirects, secure cookies, and one-hour HSTS are enabled for the staging host.

The default staging origin is `https://campushub-python-staging.onrender.com`. If Render assigns another hostname, update `DJANGO_PUBLIC_URL`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS` together. Add `https://campushub-python-staging.onrender.com/auth/callback` to the staging Supabase Auth allowed redirect URLs. Do not change the production Supabase Site URL or production OAuth callback during staging.

Staging remains isolated verification only and must never write to production data. Signed download URLs are bearer links and remain usable until they expire; do not publish them in logs or share them outside the intended audience.

## Production deployment

The Render Blueprint defines a `campushub-python-production` compatibility service with automatic deploys disabled. The old Vercel alias proxies to this service; the maintained Vercel project deploys the Django app directly from the `python_app` root. Render releases are deployed manually from `main`.

Configure the production service with the existing production Supabase PostgreSQL connection string, Supabase URL and publishable key, plus the server-only legacy `service_role` JWT required by the storage helper. Keep `SUPABASE_STORAGE_BUCKET` set to the existing `campushub-files` bucket so existing public file references continue to work. That bucket is public, so configure a separate private `campushub-python-files` bucket as `SUPABASE_UPLOAD_BUCKET`; new Python uploads are stored there with bucket-qualified references, while pre-existing public references continue to resolve through the legacy bucket. Do not make the existing bucket private or use staging credentials. Set `DJANGO_PUBLIC_URL` to the exact production-facing origin, `DJANGO_ALLOWED_HOSTS` to the exact Render and Vercel hostnames, and `DJANGO_CSRF_TRUSTED_ORIGINS` to the HTTPS production origin. Keep all secrets in Render environment settings.

### Email ownership verification

Email/password signups use the existing Supabase Auth project. In Supabase Auth settings, enable email confirmations for the Email provider and configure production SMTP for reliable delivery. Set the Site URL to `https://campushub-python.vercel.app` and add `https://campushub-python.vercel.app/auth/email/confirm/` to the allowed redirect URLs. Add the matching local confirmation URL while developing locally. Do not disable email confirmations: the app refuses to create a CampuZHub account if Supabase returns an immediate session instead of requiring confirmation.

New accounts are created in CampuZHub only after the confirmation link returns a verified Supabase identity. Existing email/password CampuZHub accounts are prompted to verify their email on their next successful password login before the app establishes a session. Google sign-in remains verified by Google/Supabase. The login page can resend a pending confirmation email.

The production health endpoint, database connection, Google OAuth provider redirect, and private bucket upload/signed-download path have been smoke-tested. Complete an account-based sign-in and authenticated workflow acceptance test after deployment; do not create test accounts or write sample records to the production database. Retain the legacy Vercel alias and Render compatibility service unless they are deliberately retired.

The approved branch-specific diploma subject catalogs can be applied together with [`sql/replace_all_branch_subjects.sql`](sql/replace_all_branch_subjects.sql). It replaces subjects for CSE, Civil, Electrical, ECE, Mechanical, and MLT with the supplied branch-specific lists plus only the common subjects mapped to each branch. Repeated subject names automatically include their branch code. It does not add semester labels or unlisted general subjects. The transaction stops if any required branch is missing or any current subject has linked study notes; existing tools are detached from replaced subjects.

[`sql/rename_duplicate_subjects_with_branch_code.sql`](sql/rename_duplicate_subjects_with_branch_code.sql) adds branch-code suffixes to the current duplicated subject names without changing subject IDs or linked records.

[`sql/remove_cse_elective.sql`](sql/remove_cse_elective.sql) removes only the CSE Elective entry from that catalog; it refuses to run if study notes are attached.

The ECE branch display name can be updated with [`sql/rename_ece_branch.sql`](sql/rename_ece_branch.sql), which renames its existing `ECE` record without changing its ID or code.

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
- Dedicated branch toolkits for CSE, Mechanical, Electrical, Electronics, Civil and MLT, including stateless calculators, programming practice, circuit/reference helpers, and MLT study practice. The CSE SQL lab runs read-only queries against a fictional in-memory dataset; the Linux terminal runs commands only against a temporary browser-side virtual filesystem.
- Branch-scoped study resources: signed-in students and branch teacher accounts are limited to their assigned branch; teacher uploads display the branch identity.
- Student calculators and study utilities: percentage, CGPA, general/mechanical unit conversions, Python concept practice, read-only SQL query practice, simulated Linux command practice, IPv4 subnetting, Ohm's law, power, logic gates, area/volume, and dilution calculations.
- A restored 10-language Code Lab: Python executes in a browser Web Worker with interactive `input()` and time/output bounds; nine languages use the OneCompiler cloud API.
- Email/password sign-in with bcrypt-compatible hashes, Supabase Google OAuth using PKCE, and student profile editing.
- BookShare listings and request/accept/reject/return flows.
- SkillSwap teach/learn listings, reciprocal requests, two-sided completion, and feedback.
- Help requests and owner resolution, a project idea catalog/submissions, and staff content/role administration.
- PDF/PNG/JPG academic-resource and campus-notice uploads plus ZIP/PDF/PNG/JPG student project attachments to Supabase Storage (10 MB maximum; MIME/extension and file-signature checks).

Branch calculators and short practice sets are processed per request and do not write attempts to PostgreSQL. The SQL sandbox blocks writes and limits query time and returned rows; its in-memory sample data is recreated on every run. The Linux terminal modifies only its browser-memory practice filesystem. The HTML playground runs inside an isolated sandboxed iframe with a restrictive Content Security Policy. The MLT tools are educational only and do not provide diagnosis or treatment guidance.

## Campus board and student planner

The campus board at `/campus/` reuses existing announcements and displays upcoming campus events. Staff can publish events from the admin page; teachers are limited to their assigned branch. Student timetables and assignment trackers are private per account at `/planner/`.

These features use three additive PostgreSQL tables and do not alter existing tables. Before deploying this feature to a Supabase environment, run `python_app/sql/add_campus_features.sql` against that environment. Keep staging and production databases separate. Django models for these existing Supabase tables are unmanaged, so do not run `makemigrations` or `migrate` to create them.

The existing Code Lab route/shell is intentionally kept separate and is not redesigned. Python Code Lab execution was verified in a local browser; the nine OneCompiler-backed languages are mocked in unit tests and have not been run against the external service. Code and stdin for those nine languages are sent to OneCompiler, so the UI warns users not to include private data. The Python Basics Practice utility is a fixed concept quiz and never executes arbitrary code. Features requiring tables absent from the existing schema (for example help replies, quizzes/practicals, team memberships, reports, and notifications) are not claimed as implemented. Database writes, live OAuth, and real Storage uploads still require isolated end-to-end verification.

## Existing database and deployment safety

All mapped Supabase models are unmanaged; do not run Django migrations against the existing database. Other than the explicitly approved additive note, project, and announcement fields documented below, do not create or alter production tables.

The approved teacher/AI resource split adds one `source_type` discriminator to the existing `notes` table. This additive migration has been applied to the configured Supabase database; for another environment, run `sql/add_note_source_type.sql` once before deploying code that reads this field. Existing uploads keep the default `teacher` category. The baseline `sql/schema.sql` includes the field for fresh databases.

Campus notice attachments add nullable `attachment_url` and `attachment_name` fields to the existing `announcements` table. This additive migration has been applied to the configured Supabase database; run `sql/add_announcement_attachments.sql` once in other environments before publishing a notice with an attachment. The baseline schema includes both fields for fresh databases. Only admins and super-admins are offered the optional PDF/PNG/JPG upload.

The Django app filters study-resource search and BranchHub navigation to a signed-in non-admin account's assigned branch, and subject resource pages require a signed-in account from that branch (admins can access all branches). In the Python app, notes and attachments are stored in a private Supabase Storage bucket; signed links are generated only when the corresponding authorized page is rendered and expire after one hour.

Student project attachments add nullable `attachment_url` and `attachment_name` fields to the existing `projects` table. This additive migration has been applied to the configured Supabase database; run `sql/add_project_attachments.sql` once in other environments before using this upload feature. The baseline schema includes both fields for new databases. Attachments are optional and are limited to ZIP/PDF/PNG/JPG files up to 10 MB.

Google OAuth uses Supabase's callback. For local testing, add `http://127.0.0.1:8000/auth/callback` to Supabase Auth's allowed redirects; retain the current Site URL and existing callback URLs. Configure `DJANGO_PUBLIC_URL` only for an intended Django deployment. Keep the Supabase service-role key server-side; it is used only by the Storage upload helper.
