# CampuZHub

CampuZHub is a student platform for learning, sharing resources, finding project ideas, and running code. The maintained application is the Django edition in `python_app/`. The public website address remains `campushub-python.vercel.app` while the displayed product branding changes.

## Production

The Python application is deployed at [campushub-python.vercel.app](https://campushub-python.vercel.app/) with the Vercel project root set to `python_app`. It uses the existing Supabase PostgreSQL database and Auth project. Database models are unmanaged; **do not run Django schema migrations against the production database**.

The previous `campushub-opal.vercel.app` domain is retained as a compatibility alias. Its Vercel project uses [client/vercel.json](client/vercel.json) to forward requests to the existing Python Render production service. Keep that configuration until the alias is intentionally migrated. The Render service and isolated staging service are defined in [render.yaml](render.yaml).

The former React/Vite frontend and Express API source have been removed. The remaining SQL files under `python_app/sql/` document the existing schema and additive changes; they are reference/maintenance scripts, not Django migrations.

## Local development

See the [Python app setup and deployment guide](python_app/README.md). In short:

```powershell
py -m venv python_app\.venv
python_app\.venv\Scripts\Activate.ps1
python -m pip install -r python_app\requirements.txt
Copy-Item python_app\.env.example python_app\.env
python python_app\manage.py check
python python_app\manage.py runserver
```

Do not commit `.env` files or share credentials in chat. Keep Supabase service-role keys and database URLs server-side.
