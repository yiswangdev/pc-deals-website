# 🚀 PCDeals

A full-stack web application for discovering and tracking **PC component deals** in real time. Built with **Next.js** and **FastAPI**, and deployed on **Vercel**.

This app focuses on deals for parts and peripherals such as **GPUs, CPUs, RAM, SSDs, motherboards, power supplies, cooling, and monitors**.

---

## 🌐 Live Demo

- **Frontend:** https://pc-deals-frontend.vercel.app  
- **Backend API:** https://pc-deals-backend.vercel.app/api  

---

## 🧱 Tech Stack

**Frontend**
- Next.js
- React
- TypeScript
- Tailwind CSS

**Backend**
- FastAPI
- Python
- JWT Authentication

**Infrastructure**
- Vercel (Frontend + Serverless Backend)
- Vercel Cron Jobs

---

## ⚙️ Architecture

This project is deployed as two separate Vercel applications:

```
frontend/   → Next.js UI
backend/    → FastAPI API
```

The frontend communicates with the backend via REST APIs.

---

## 🔐 Environment Variables

### Frontend

```
NEXT_PUBLIC_API_URL=https://pc-deals-backend.vercel.app/api
```

---

### Backend

```
APP_ENV=production
JWT_SECRET_KEY=your_super_secure_secret
JWT_EXPIRE_MINUTES=1440

ALLOWED_ORIGINS=https://pc-deals-frontend.vercel.app
SITE_URL=https://pc-deals-frontend.vercel.app
```

---

### Optional

```
RESEND_API_KEY=
EMAIL_FROM=

REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=pcdeals/1.0

CRON_SECRET=
```

---

## 🚀 Deployment (Vercel)

### Backend
- Create a Vercel project
- Set Root Directory to `backend`
- Add environment variables
- Deploy

### Frontend
- Create another Vercel project
- Set Root Directory to `frontend`
- Add:

```
NEXT_PUBLIC_API_URL=https://pc-deals-backend.vercel.app/api
```

- Deploy

### Final Step
Update backend environment variables:

```
ALLOWED_ORIGINS=https://pc-deals-frontend.vercel.app
SITE_URL=https://pc-deals-frontend.vercel.app
```

Redeploy backend.

---

## ⏱️ Cron Jobs (Optional)

Add to `backend/vercel.json`:

```json
{
  "crons": [
    { "path": "/api/cron/refresh", "schedule": "0 * * * *" },
    { "path": "/api/cron/daily-alerts", "schedule": "0 8 * * *" }
  ]
}
```

---

## 💻 Local Development

### Backend

```
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

---

### Frontend

```
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## 📦 Project Structure

```
pc-deals/
├── frontend/
├── backend/
└── README.md
```

---

## 🔒 Security

- Do not commit `.env` files
- Store secrets in Vercel environment variables

---

## ⚠️ Common Issues

**CORS errors**
```
ALLOWED_ORIGINS=https://pc-deals-frontend.vercel.app
```

**API not working**
```
NEXT_PUBLIC_API_URL=https://pc-deals-backend.vercel.app/api
```

---

## 📄 License

MIT License
