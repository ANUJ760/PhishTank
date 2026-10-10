"""Authentication and session management using PostgreSQL."""
from __future__ import annotations
import hashlib
import os
import secrets
import time
import uuid
from typing import Optional
from fastapi import Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from backend.registry import db
from backend.http.schemas import UserResponse


SESSION_COOKIE_NAME = "gc_session"
SESSION_DURATION_S = 7 * 24 * 3600  # 7 days


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, expected_hex = hashed.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return secrets.compare_digest(dk.hex(), expected_hex)
    except Exception:
        return False


def get_user_by_email(email: str) -> Optional[dict]:
    with db._connect() as connection:
        row = connection.execute(
            "SELECT id, email, password_hash, name, role FROM users WHERE email = %s",
            (email.strip().lower(),),
        ).fetchone()
        if not row:
            return None
        return {"id": row[0], "email": row[1], "password_hash": row[2], "name": row[3], "role": row[4]}


def get_user_by_id(user_id: str) -> Optional[dict]:
    with db._connect() as connection:
        row = connection.execute(
            "SELECT id, email, password_hash, name, role FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return {"id": row[0], "email": row[1], "password_hash": row[2], "name": row[3], "role": row[4]}


def create_user(name: str, email: str, password: str, role: str = "coordinator") -> dict:
    existing = get_user_by_email(email)
    if existing:
        raise ValueError("User with this email already exists")
    user_id = f"U_{uuid.uuid4().hex[:12]}"
    pwd_hash = hash_password(password)
    now = time.time()
    with db._connect() as connection:
        connection.execute(
            "INSERT INTO users(id, email, password_hash, name, role, created_at) VALUES(%s, %s, %s, %s, %s, %s)",
            (user_id, email.strip().lower(), pwd_hash, name.strip(), role, now),
        )
    return {"id": user_id, "email": email.strip().lower(), "name": name.strip(), "role": role}


def create_session(user_id: str) -> str:
    session_id = secrets.token_urlsafe(32)
    now = time.time()
    expires_at = now + SESSION_DURATION_S
    with db._connect() as connection:
        connection.execute(
            "INSERT INTO sessions(id, user_id, created_at, expires_at) VALUES(%s, %s, %s, %s)",
            (session_id, user_id, now, expires_at),
        )
    return session_id


def delete_session(session_id: str) -> None:
    if not session_id:
        return
    with db._connect() as connection:
        connection.execute("DELETE FROM sessions WHERE id = %s", (session_id,))


def get_user_by_session(session_id: str) -> Optional[dict]:
    if not session_id:
        return None
    now = time.time()
    with db._connect() as connection:
        row = connection.execute(
            "SELECT u.id, u.email, u.password_hash, u.name, u.role FROM sessions s "
            "JOIN users u ON s.user_id = u.id WHERE s.id = %s AND s.expires_at > %s",
            (session_id, now),
        ).fetchone()
        if not row:
            return None
        return {"id": row[0], "email": row[1], "password_hash": row[2], "name": row[3], "role": row[4]}


def seed_demo_users():
    """Ensure baseline demo accounts exist."""
    db.init_db()
    demo_accounts = [
        ("Demo Coordinator", "admin@gecompose.internal", "password123", "coordinator"),
        ("Prof. Rao", "rao@gecompose.internal", "password123", "reviewer"),
        ("Prof. Mehta", "mehta@gecompose.internal", "password123", "reviewer"),
        ("Dean Academics", "dean@gecompose.internal", "password123", "reviewer"),
    ]
    for name, email, pwd, role in demo_accounts:
        if not get_user_by_email(email):
            create_user(name, email, pwd, role)


# FastAPI Dependencies

async def get_current_user_optional(request: Request) -> Optional[UserResponse]:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        # Check Authorization Bearer header as fallback
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_id = auth_header[7:].strip()
    if not session_id:
        return None
    user_dict = get_user_by_session(session_id)
    if not user_dict:
        return None
    return UserResponse(
        id=user_dict["id"],
        email=user_dict["email"],
        name=user_dict["name"],
        role=user_dict["role"],
    )


async def require_user(
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
) -> UserResponse:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
        )
    return current_user


async def get_user_or_demo(
    current_user: Optional[UserResponse] = Depends(get_current_user_optional),
) -> UserResponse:
    if current_user is not None:
        return current_user
    return UserResponse(
        id="demo-user",
        email="admin@gecompose.internal",
        name="Coordinator",
        role="coordinator",
    )


async def require_coordinator(
    current_user: UserResponse = Depends(require_user),
) -> UserResponse:
    if current_user.role not in {"coordinator", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coordinator permission required for this operation.",
        )
    return current_user
