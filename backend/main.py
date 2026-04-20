from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import routers.alerts as alerts
import routers.auth as auth
import routers.deals as deals
from routers.alerts import _load_users, _save_users, send_alert_email_to_user
from services.rss import refresh_deals_cache

load_dotenv()

scheduler = AsyncIOScheduler()
IS_VERCEL = os.getenv("VERCEL") == "1"
CRON_SECRET = os.getenv("CRON_SECRET")


async def send_daily_alerts() -> None:
    users = _load_users()
    sent_at = datetime.now(timezone.utc).isoformat()
    for user in users:
        alert_config = user.get("alert_config") or {}
        if not alert_config.get("enabled"):
            continue
        try:
            await send_alert_email_to_user(user, alert_kind="daily")
            user["alert_config"]["last_daily_sent_at"] = sent_at
        except Exception as exc:
            print(f"[Alerts] Failed to send daily alert to {user.get('email')}: {exc}")
    _save_users(users)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await refresh_deals_cache()
    if not IS_VERCEL:
        scheduler.add_job(refresh_deals_cache, "interval", hours=1, id="rss_refresh")
        scheduler.add_job(
            send_daily_alerts,
            CronTrigger(hour=8, minute=0),
            id="daily_alerts",
            replace_existing=True,
        )
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(
    title="PC Deals API",
    description="Real-time PC component deals aggregator via RSS",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deals.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")


def _verify_cron(auth_header: str | None) -> None:
    if not CRON_SECRET:
        return
    if auth_header != f"Bearer {CRON_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized cron request")


@app.get("/")
async def root():
    return {"status": "online", "service": "PC Deals API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "scheduler": "disabled-on-vercel" if IS_VERCEL else "local"}


@app.get("/api/cron/refresh")
async def cron_refresh(authorization: str | None = Header(default=None)):
    _verify_cron(authorization)
    await refresh_deals_cache()
    return {"status": "refreshed"}


@app.get("/api/cron/daily-alerts")
async def cron_daily_alerts(authorization: str | None = Header(default=None)):
    _verify_cron(authorization)
    await send_daily_alerts()
    return {"status": "daily alerts sent"}
