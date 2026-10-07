# CampusHub Python edition

This Django app is an isolated, side-by-side migration. It does not replace the existing React/Express deployment and does not run database migrations against the existing Supabase schema.

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

The Python app reads environment values from `python_app/.env` first and then the existing ignored `server/.env`. Configure `DATABASE_URL` with the existing Supabase PostgreSQL connection string; never commit either `.env` file.

For an initial UI-only run without a database connection, Django uses a local SQLite file. The live Supabase tables are mapped as unmanaged Django models, so ordinary app startup does not create or alter those tables. `/health/` reports whether PostgreSQL is connected.

The initial port includes the Python home page, branch directory, and a health endpoint. Other feature links are explicit in-progress placeholders. Supabase Auth/Storage integration will use Python HTTP calls, while Django ORM/psycopg connect to the existing database. Google login, account/session handling, and remaining product features will be ported and tested before any production switch.
