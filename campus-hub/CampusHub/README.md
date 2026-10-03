# CampusHub — Learn • Share • Build • Grow

CampusHub is a full-stack student ecosystem starter for Polytechnic/College campuses.

## Included in this starter

- React + Vite frontend
- Responsive dark/glass-inspired UI
- Node.js + Express API
- PostgreSQL schema and seed script
- JWT authentication with roles
- Student registration and login
- BranchHub for CSE, Mechanical, Electrical, Electronics, Civil and MLT
- Subject catalog
- Notes listing and admin PDF/PNG/JPG upload
- Announcements
- BookShare listings and requests
- SkillSwap listings
- Basic admin dashboard and stats
- Mini tools: percentage, CGPA, Ohm's law, power, area/volume, logic gates, Linux helper
- Optional Supabase Storage integration for persistent production files
- Vercel SPA config
- Render web-service config

## Important architecture decision

Calculators and other purely client-side tools do not need the database.
The database is for persistent data such as users, notes metadata, announcements, books, skills, projects and history.

For production, use a managed PostgreSQL database (Supabase is a convenient option) instead of a PostgreSQL instance running on your own laptop.

## Local demo mode

This project is bundled with a browser-based demo fallback so it can run immediately without a PostgreSQL instance. If the backend is unavailable, CampusHub automatically uses a seeded in-browser dataset with a demo admin account.

Demo admin credentials:

- Email: `admin@campushub.local`
- Password: `demo-admin`

The browser demo also accepts `ChangeMe123!` for this demo admin, matching the default seed password used by the PostgreSQL setup below.

This is useful for local UI testing and prototype presentations before connecting your PostgreSQL backend.

## Local setup

### 1. Install

- Node.js 20+
- PostgreSQL 15+
- Git

### 2. Create database

Create a database named `campushub` in PostgreSQL.

Copy `server/.env.example` to `server/.env` and update `DATABASE_URL` and `JWT_SECRET`.

### 3. Install dependencies

From the project root:

```bash
npm install --workspace client
npm install --workspace server
```

### 4. Seed the database

```bash
npm run seed --workspace server
```

The seed command creates branches, subjects, tools and a first super-admin account. Run it from the project root; the script loads `server/.env` automatically.
Default admin credentials are:

- Email: `admin@campushub.local`
- Password: `ChangeMe123!`

**Change the password/seed env before any public deployment.**

### 5. Start API

```bash
npm run dev --workspace server
```

API: `http://localhost:5000`

### 6. Start frontend

In a second terminal:

```bash
npm run dev --workspace client
```

Frontend: `http://localhost:5173`

## Production file storage

The backend supports two modes:

1. Local storage (development only)
2. Supabase Storage (required for production note files)

Set these server environment variables to enable Supabase Storage:

```env
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=campushub-files
```

Create a storage bucket with the same name in Supabase. For public note PDFs, configure the bucket/read policy appropriately. Keep the service-role key only on the backend. In production, the API intentionally refuses to fall back to ephemeral local storage.

## Deployment plan (₹0-oriented)

Recommended split:

```text
GitHub
  ├── client → Vercel
  └── server → Render Web Service

Supabase
  ├── PostgreSQL database
  └── Storage bucket for PDFs/images
```

Set:

### Vercel

Project root: `client`

Environment variable:

```env
VITE_API_URL=https://YOUR-BACKEND-URL/api
```

### Render

Project root: `server`

Environment variables:

```env
NODE_ENV=production
CLIENT_URL=https://YOUR-VERCEL-DOMAIN
DATABASE_URL=YOUR-SUPABASE-POSTGRES-CONNECTION-STRING
JWT_SECRET=LONG_RANDOM_SECRET
SUPABASE_URL=YOUR_SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
SUPABASE_STORAGE_BUCKET=campushub-files
PORT=10000
```

## Security checklist before public launch

- Change seeded admin credentials.
- Generate a long random JWT secret.
- Never put the Supabase service-role key in frontend code.
- Keep CORS restricted to the deployed frontend origin.
- Add rate limiting before a large public launch.
- Add pagination to large lists.
- Add moderation/report workflows for user-generated content.
- Put online code execution in an isolated sandbox; never execute student code directly in the main API process.
- Add backups/export procedures for academic content.

## What is deliberately not implemented yet

- Real compiler execution/sandbox
- Full BookShare accept/return workflow
- SkillSwap matching algorithm
- Inter-branch project teams
- Practical Vault CMS
- Viva/MCQ question bank UI
- Notifications/email
- Teacher-specific permissions beyond the starter role
- Advanced admin CRUD for every content type
- AI tools (so the base project does not require paid API keys)

These are designed as the next modules so the current project remains a manageable MVP.
