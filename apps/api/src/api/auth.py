import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.core.config import settings
from src.core.rate_limiter import check_guest_auth_rate_limit
from src.db.models import GuestSession, User, UserRole
from src.db.session import get_db
from src.schemas.auth import (
    AuthCredentials,
    AuthResponse,
    GuestSessionResponse,
    LogoutResponse,
    RegisterRequest,
    UserResponse,
)

logger = logging.getLogger("quorum.api.auth")

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
    if current_user.role == UserRole.GUEST.value:
        return UserResponse(
            id=current_user.id,
            email="",
            name="Guest Judge",
            role=UserRole.GUEST,
        )
    return UserResponse.model_validate(current_user)


@router.post(
    "/guest",
    response_model=GuestSessionResponse,
    dependencies=[Depends(check_guest_auth_rate_limit)],
    summary="Create a cookie-backed Guest Judge session",
)
async def guest_login(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> GuestSessionResponse:
    """
    Issues a dedicated Guest Judge session.
    Persists a GuestSession row with a unique jti for isolated per-session revocation.
    Sets HttpOnly quorum_session cookie.
    Returns safe session metadata only (no raw tokens/JWTs).
    """
    guest_email = "judge@quorum.ai"
    result = await db.execute(select(User).where(User.email == guest_email))
    guest_user = result.scalars().first()
    if not guest_user:
        guest_user = User(
            id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
            email=guest_email,
            name="Guest Judge",
            role=UserRole.GUEST.value,
        )
        db.add(guest_user)
        await db.commit()
        await db.refresh(guest_user)
    elif guest_user.role != UserRole.GUEST.value:
        guest_user.role = UserRole.GUEST.value
        await db.commit()
        await db.refresh(guest_user)

    jti = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=4)

    raw_ua = request.headers.get("user-agent", "")
    safe_ua = raw_ua[:256] if raw_ua else None

    session_record = GuestSession(
        id=jti,
        user_id=guest_user.id,
        session_type="guest",
        issued_at=now,
        expires_at=expires_at,
        revoked_at=None,
        user_agent=safe_ua,
    )
    db.add(session_record)
    await db.commit()

    token_claims = {
        "sub": str(guest_user.id),
        "jti": str(jti),
        "role": "guest",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    signed_jwt = jwt.encode(token_claims, _secret(), algorithm="HS256")

    is_secure = (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto") == "https"
    ) and (settings.ENVIRONMENT != "development")
    response.set_cookie(
        key="quorum_session",
        value=signed_jwt,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=4 * 3600,
        path="/",
    )

    return GuestSessionResponse(
        success=True,
        session_type="guest",
        role="guest",
        expires_at=expires_at.isoformat(),
    )


@router.post("/logout", response_model=LogoutResponse, summary="Revoke session and clear cookies")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    """
    Idempotently revokes the current session if it is a GuestSession.
    Only the caller's specific jti is marked revoked.
    Other concurrent guest sessions remain untouched.
    Clears the HttpOnly quorum_session cookie.
    """
    token = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif not token:
        token = request.cookies.get("quorum_session")

    if token:
        try:
            payload = jwt.decode(
                token,
                _secret(),
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
            jti_str = payload.get("jti")
            sub_str = payload.get("sub")
            if jti_str and sub_str:
                jti_uuid = uuid.UUID(str(jti_str))
                sub_uuid = uuid.UUID(str(sub_str))
                now = datetime.now(timezone.utc)
                stmt = (
                    update(GuestSession)
                    .where(
                        GuestSession.id == jti_uuid,
                        GuestSession.user_id == sub_uuid,
                        GuestSession.revoked_at.is_(None),
                    )
                    .values(revoked_at=now)
                )
                await db.execute(stmt)
                await db.commit()
                logger.info(f"[LOGOUT] Revoked guest session {jti_uuid} for user {sub_uuid}")
        except Exception as exc:
            logger.debug(f"[LOGOUT] Could not decode token during logout revocation: {exc}")

    response.delete_cookie(
        key="quorum_session",
        path="/",
        httponly=True,
        samesite="lax",
    )
    return LogoutResponse(success=True, message="Logged out successfully")

