# PCDeals — Vercel-ready package

This package keeps the existing UI and app structure intact, while fixing deploy-sensitive issues for Vercel.

## What was fixed

- Removed reliance on the root `vercel.json` multi-service setup.
  - Vercel Services is still in private beta and is not the safest default deployment path.
- Added safer frontend API defaults:
  - `NEXT_PUBLIC_API_URL` now falls back to `/api` in the client
  - `next.config.js` now falls back to localhost for local dev
- Added backend storage guards so `backend/data/users.json` is created if missing
- Disabled APScheduler automatically on Vercel
  - Vercel is serverless, so in-process schedulers are not reliable there
- Added Vercel-friendly cron endpoints:
  - `GET /api/cron/refresh`
  - `GET /api/cron/daily-alerts`
- Pinned missing backend dependencies in `backend/requirements.txt`
- Added `.env.example` files and a root `.gitignore`
- Cleaned out local-only and unnecessary files from the deliverable

## Recommended Vercel deployment

Deploy this as **two Vercel projects** from the same repo:

1. **Backend project** using `backend/` as the Root Directory
2. **Frontend project** using `frontend/` as the Root Directory

This is the most reliable approach for this codebase right now.

---

## Backend deployment on Vercel

### Root Directory
Set the Vercel project Root Directory to:

```text
backend
```

### Framework
Vercel should detect FastAPI automatically.

### Required backend environment variables
Set these in the backend Vercel project:

```text
APP_ENV=production
ALLOWED_ORIGINS=https://YOUR-FRONTEND-DOMAIN.vercel.app
JWT_SECRET_KEY=YOUR-STRONG-SECRET
JWT_EXPIRE_MINUTES=1440
SITE_URL=https://YOUR-FRONTEND-DOMAIN.vercel.app
```

### Optional backend environment variables
Only add these if you use them:

```text
RESEND_API_KEY=...
EMAIL_FROM=PC Deals <your-verified-email@yourdomain.com>
CRON_SECRET=YOUR-CRON-SECRET
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=pcdeals/1.0
```

### Backend cron jobs on Vercel
Because APScheduler is disabled on Vercel, use Vercel Cron Jobs instead.

In the backend Vercel project, add these cron jobs in `vercel.json` **only if you want scheduled tasks**:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "crons": [
    {
      "path": "/api/cron/refresh",
      "schedule": "0 * * * *"
    },
    {
      "path": "/api/cron/daily-alerts",
      "schedule": "0 8 * * *"
    }
  ]
}
```

If you set `CRON_SECRET`, configure the cron requests to include it using your chosen protection pattern.

---

## Frontend deployment on Vercel

### Root Directory
Set the Vercel project Root Directory to:

```text
frontend
```

### Framework
Vercel should detect Next.js automatically.

### Required frontend environment variables
Set this in the frontend Vercel project:

```text
NEXT_PUBLIC_API_URL=https://YOUR-BACKEND-DOMAIN.vercel.app/api
```

Optional:

```text
NEXT_PUBLIC_APP_NAME=PCDeals
NEXT_PUBLIC_ENABLE_NOTIFICATIONS=true
```

---

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## Files that should not be committed or deployed

These were unnecessary and should stay out of the repo/deployment bundle:

- `.git/`
- `frontend/.next/`
- `backend/venv/`
- `backend/__pycache__/`
- `.env`
- `.env.local`

---

## Notes

- The app structure and UI were not changed.
- The recommended deployment path is two Vercel projects, not one combined root deploy.
- If you have access to Vercel Services beta, a single-project deployment is possible, but it is not the default setup I prepared here.
