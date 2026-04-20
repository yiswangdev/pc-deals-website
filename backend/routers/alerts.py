from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import json

from services.email_service import (
    send_email,
    build_deals_email,
    build_test_email,
    resend_configured,
)
from services.rss import get_cached_deals
from routers.auth import get_current_user

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
USERS_FILE = BASE_DIR / "data" / "users.json"


def _ensure_storage() -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")


class AlertConfig(BaseModel):
    enabled: bool
    categories: List[str]


def _ensure_user_defaults(user: Dict[str, Any]) -> Dict[str, Any]:
    alert_config = user.get("alert_config") or {}
    user["alert_config"] = {
        "enabled": bool(alert_config.get("enabled", False)),
        "categories": alert_config.get("categories") or ["GPU", "CPU", "RAM", "SSD"],
        "last_initial_sent_at": alert_config.get("last_initial_sent_at"),
        "last_daily_sent_at": alert_config.get("last_daily_sent_at"),
    }
    return user


def _load_users():
    _ensure_storage()
    with USERS_FILE.open("r", encoding="utf-8") as f:
        users = json.load(f)
    return [_ensure_user_defaults(u) for u in users]



def _save_users(users):
    _ensure_storage()
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)



def _filter_deals_for_categories(categories: List[str]) -> List[Dict[str, Any]]:
    cached = get_cached_deals()
    all_deals = cached.get("deals", [])
    if categories:
        return [d for d in all_deals if d.get("category") in categories]
    return all_deals


async def send_alert_email_to_user(user: Dict[str, Any], alert_kind: str = "daily") -> Dict[str, Any]:
    if not resend_configured():
        raise RuntimeError("Email not configured — set RESEND_API_KEY in .env")

    user = _ensure_user_defaults(user)
    selected_cats = user["alert_config"].get("categories", [])
    filtered = _filter_deals_for_categories(selected_cats)

    if filtered:
        html = build_deals_email(user["email"], filtered, selected_cats, alert_kind=alert_kind)
        prefix = "Initial" if alert_kind == "initial" else "Daily"
        subject = f"PCDeals {prefix} Alert — Top {min(10, len(filtered))} Deals"
    else:
        html = build_test_email(user["email"], selected_cats)
        prefix = "Initial" if alert_kind == "initial" else "Daily"
        subject = f"PCDeals {prefix} Alert — No Matching Deals Yet"

    await send_email(
        to=user["email"],
        subject=subject,
        html=html,
    )

    return {
        "message": f"{alert_kind.title()} alert sent to {user['email']} with {min(10, len(filtered))} deals",
        "count": min(10, len(filtered)),
    }


@router.put("/alerts/config")
async def save_config(payload: AlertConfig, user=Depends(get_current_user)):
    users = _load_users()

    for u in users:
        if u["email"].lower() == user["email"].lower():
            previous_enabled = bool((u.get("alert_config") or {}).get("enabled", False))
            existing = _ensure_user_defaults(u)["alert_config"]
            existing["enabled"] = payload.enabled
            existing["categories"] = payload.categories
            u["alert_config"] = existing
            _save_users(users)

            initial_alert_sent = False
            if payload.enabled and not previous_enabled:
                try:
                    await send_alert_email_to_user(u, alert_kind="initial")
                    u["alert_config"]["last_initial_sent_at"] = datetime.now(timezone.utc).isoformat()
                    _save_users(users)
                    initial_alert_sent = True
                except Exception as exc:
                    raise HTTPException(status_code=500, detail=f"Saved config, but failed to send initial alert: {exc}")

            return {
                "message": "saved",
                "alert_config": u["alert_config"],
                "initial_alert_sent": initial_alert_sent,
            }

    raise HTTPException(status_code=404, detail="User not found")


@router.post("/alerts/test")
async def test_email(user=Depends(get_current_user)):
    try:
        result = await send_alert_email_to_user(user, alert_kind="test")
        return {"message": result["message"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
