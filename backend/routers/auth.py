from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import hmac
import json
import os
import secrets
import jwt

router = APIRouter()
security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _ensure_storage():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")


def _load_users():
    _ensure_storage()
    with USERS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_users(users):
    _ensure_storage()
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def _find_user_by_email(email: str):
    users = _load_users()
    for user in users:
        if user["email"].lower() == email.lower():
            return user
    return None


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()


def _make_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = _hash_password(password, salt)
    return f"{salt}${hashed}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split("$", 1)
    except ValueError:
        return False
    check = _hash_password(password, salt)
    return hmac.compare_digest(check, hashed)


def create_access_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": email,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = _find_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


@router.post("/register")
async def register(payload: RegisterRequest):
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    users = _load_users()

    if any(u["email"].lower() == payload.email.lower() for u in users):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = {
        "email": payload.email,
        "password_hash": _make_password_hash(payload.password),
        "alert_config": {
            "enabled": False,
            "categories": ["GPU", "CPU", "RAM", "SSD"],
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    users.append(user)
    _save_users(users)

    token = create_access_token(user["email"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "alert_config": user["alert_config"],
        },
    }


@router.post("/login")
async def login(payload: LoginRequest):
    user = _find_user_by_email(payload.email)

    if not user or not _verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user["email"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "alert_config": user.get("alert_config", {"enabled": False, "categories": []}),
        },
    }


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {
        "email": user["email"],
        "alert_config": user.get("alert_config", {"enabled": False, "categories": []}),
    }