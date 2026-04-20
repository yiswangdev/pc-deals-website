from datetime import datetime
from typing import Optional
import os
import hashlib
import hmac
import base64
import json
import time

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

_users: dict[str, dict] = {}


def _hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000)
    return f"{salt}:{hashed.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split(":", 1)
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000)
        return hmac.compare_digest(check.hex(), hashed)
    except Exception:
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _create_jwt(payload: dict) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = dict(payload, iat=int(time.time()))
    body = _b64(json.dumps(payload).encode())
    sig_input = f"{header}.{body}".encode()
    sig = _b64(hmac.new(SECRET_KEY.encode(), sig_input, hashlib.sha256).digest())
    return f"{header}.{body}.{sig}"


def _verify_jwt(token: str) -> Optional[dict]:
    try:
        header, body, sig = token.split(".")
        sig_input = f"{header}.{body}".encode()
        expected = _b64(hmac.new(SECRET_KEY.encode(), sig_input, hashlib.sha256).digest())

        if not hmac.compare_digest(sig, expected):
            return None

        payload = json.loads(base64.urlsafe_b64decode(body + "=="))
        exp = payload.get("exp", 0)

        if exp and time.time() > exp:
            return None

        return payload
    except Exception:
        return None


def register_user(email: str, password: str) -> dict:
    email = email.lower().strip()

    if email in _users:
        raise ValueError("Email already registered")

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    _users[email] = {
        "email": email,
        "password_hash": _hash_password(password),
        "created_at": datetime.utcnow().isoformat(),
        "alert_config": {
            "enabled": False,
            "categories": ["GPU", "CPU", "RAM", "SSD"],
            "min_discount": 0,
        },
    }

    return {"email": email}


def login_user(email: str, password: str) -> str:
    email = email.lower().strip()
    user = _users.get(email)

    if not user or not _verify_password(password, user["password_hash"]):
        raise ValueError("Invalid email or password")

    payload = {
        "sub": email,
        "exp": int(time.time()) + ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }

    return _create_jwt(payload)


def get_user_from_token(token: str) -> Optional[dict]:
    payload = _verify_jwt(token)
    if not payload:
        return None

    return _users.get(payload.get("sub"))


def update_alert_config(email: str, config: dict) -> dict:
    if email not in _users:
        raise ValueError("User not found")

    _users[email]["alert_config"].update(config)
    return _users[email]["alert_config"]


def get_alert_config(email: str) -> dict:
    user = _users.get(email)
    if not user:
        raise ValueError("User not found")
    return user["alert_config"]


def get_all_alert_subscribers() -> list[dict]:
    return [
        {"email": u["email"], "config": u["alert_config"]}
        for u in _users.values()
        if u["alert_config"].get("enabled")
    ]