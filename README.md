# 🚀 PCDeals

A full-stack web application for discovering and tracking **PC component deals** in real time. Built with **Next.js** and **FastAPI**, and deployed on **Vercel**.

This app focuses on deals for parts and peripherals such as **GPUs, CPUs, RAM, SSDs, motherboards, power supplies, cooling, and monitors**.

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

**Infrastructure**
- Vercel (Frontend + Serverless Backend)
- Vercel Cron Jobs

---

## ⚙️ Architecture

This project is deployed as two separate Vercel applications:

```text
frontend/   → Next.js UI
backend/    → FastAPI API
```

The frontend communicates with the backend via REST APIs.

---

## 🔐 Environment Variables

### Frontend

```text
NEXT_PUBLIC_API_URL = https://backend/api
```

---

### Backend

```text
APP_ENV = production
ALLOWED_ORIGINS = https://your-website
SITE_URL = https://your-website
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

```text
NEXT_PUBLIC_API_URL=https://backend/api
```

---

## 📄 License

MIT License
