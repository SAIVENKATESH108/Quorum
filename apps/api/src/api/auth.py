import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.core.config import settings
from src.db.models import User, UserRole
from src.db.session import get_db
from src.schemas.auth import AuthResponse, RegisterRequest, AuthCredentials, UserResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _secret() -> str:
    return settings.AUTH_SECRET_KEY or "local-only-change-this-auth-secret"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return f"pbkdf2_sha256$210000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "iat": now,
            "exp": now + timedelta(hours=settings.AUTH_SESSION_HOURS),
        },
        _secret(),
        algorithm="HS256",
    )


async def _authenticate(payload: AuthCredentials, db: AsyncSession) -> AuthResponse:
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalars().first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return AuthResponse(user=UserResponse.model_validate(user), token=create_access_token(user))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    email = payload.email.lower()
    existing = (await db.execute(select(User).where(User.email == email))).scalars().first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account already exists for this email")
    user = User(
        id=uuid.uuid4(),
        email=email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN if email in settings.ADMIN_EMAILS else UserRole.MEMBER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return AuthResponse(user=UserResponse.model_validate(user), token=create_access_token(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: AuthCredentials, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    return await _authenticate(payload, db)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
