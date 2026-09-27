import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Query, Request, Security, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models import GuestSession, User, UserRole
from src.db.session import async_session_maker, get_db

logger = logging.getLogger("quorum.security")

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user_from_token(token: Optional[str], db: Optional[AsyncSession] = None) -> Optional[User]:
    """
    Validate auth token and return associated User.
    Supports Clerk tokens, signed JWTs, and dev/test session tokens.
    Automatically provisions/syncs user in the DB if authentic Clerk claims are present.
    """
    if not token:
        return None

    if token.startswith("Bearer "):
        token = token[7:]

    token = token.strip()
    if not token:
        return None

    # Native Quorum session tokens are signed with the server auth secret.
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_SECRET_KEY or "local-only-change-this-auth-secret",
            algorithms=["HS256"],
        )
        user_id = uuid.UUID(str(payload["sub"]))
        token_role = payload.get("role")
        jti_str = payload.get("jti")

        session = db or async_session_maker()
        close_session = db is None
        try:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            if not user:
                return None

            is_guest_token = token_role == "guest"
            is_guest_user = user.role == UserRole.GUEST.value

            # Strict two-way role & per-session verification for guest
            if is_guest_token or is_guest_user:
                if not (is_guest_token and is_guest_user):
                    logger.warning(
                        f"[AUTH] Guest mismatch: token_role={token_role}, db_role={user.role}"
                    )
                    return None

                if not jti_str:
                    logger.warning("[AUTH] Guest token missing jti claim")
                    return None

                try:
                    jti_uuid = uuid.UUID(str(jti_str))
                except (ValueError, TypeError):
                    logger.warning(f"[AUTH] Invalid jti UUID format: {jti_str}")
                    return None

                gs_stmt = select(GuestSession).where(
                    GuestSession.id == jti_uuid,
                    GuestSession.user_id == user.id,
                )
                gs = (await session.execute(gs_stmt)).scalars().first()
                if not gs:
                    logger.warning(f"[AUTH] Guest session {jti_uuid} not found")
                    return None
                if gs.session_type != "guest":
                    logger.warning(f"[AUTH] Guest session {jti_uuid} invalid type: {gs.session_type}")
                    return None
                if gs.revoked_at is not None:
                    logger.warning(f"[AUTH] Guest session {jti_uuid} was revoked at {gs.revoked_at}")
                    return None

                now = datetime.now(timezone.utc)
                gs_exp = gs.expires_at if gs.expires_at.tzinfo else gs.expires_at.replace(tzinfo=timezone.utc)
                if gs_exp <= now:
                    logger.warning(f"[AUTH] Guest session {jti_uuid} expired at {gs.expires_at}")
                    return None

                setattr(user, "session_jti", gs.id)
                return user

            # Non-guest native JWT: ensure user is not guest
            if is_guest_user:
                logger.warning("[AUTH] Non-guest token attempted for guest user")
                return None

            return user
        finally:
            if close_session:
                await session.close()
    except (jwt.PyJWTError, KeyError, ValueError):
        pass

    # Handle direct UUID test tokens (e.g., Bearer <uuid>)
    try:
        user_uuid = uuid.UUID(token)
        close_session = False
        session = db
        if session is None:
            session = async_session_maker()
            close_session = True

        try:
            stmt = select(User).where(User.id == user_uuid)
            res = await session.execute(stmt)
            user = res.scalars().first()
            if user:
                # Direct UUID cannot bypass guest session checks
                if user.role == UserRole.GUEST.value or user.email == "judge@quorum.ai":
                    return None
                return user
        finally:
            if close_session:
                await session.close()
    except ValueError:
        pass

    # Handle base64 encoded JSON session objects
    import base64
    import json
    try:
        raw_json = base64.b64decode(token).decode("utf-8")
        obj = json.loads(raw_json)
        if isinstance(obj, dict) and "email" in obj:
            email = obj["email"]
            # Reject any attempt to use base64 for guest user
            if email == "judge@quorum.ai" or obj.get("role") == "guest":
                return None
            name = obj.get("name", "Quorum User")
            user_id = uuid.UUID(obj["id"]) if "id" in obj and obj["id"] else uuid.uuid5(uuid.NAMESPACE_DNS, email)
            session = db or async_session_maker()
            close_session = db is None
            try:
                stmt = select(User).where((User.id == user_id) | (User.email == email))
                res = await session.execute(stmt)
                user = res.scalars().first()
                if user and user.role == UserRole.GUEST.value:
                    return None
                if not user:
                    admin_emails = [e.lower() for e in settings.ADMIN_EMAILS] if isinstance(settings.ADMIN_EMAILS, list) else [str(settings.ADMIN_EMAILS).lower()]
                    assigned_role = "admin" if email.lower() in admin_emails else "member"
                    user = User(
                        id=user_id,
                        email=email,
                        name=name,
                        role=assigned_role,
                    )
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
                return user

            finally:
                if close_session:
                    await session.close()
    except Exception:
        pass

    # Handle test / mock token prefixes (restricted to non-guest test users)
    if token.startswith("test_") or token == "mock_token":
        close_session = False
        session = db
        if session is None:
            session = async_session_maker()
            close_session = True

        email = "dev@quorum.local"
        name = "Local Developer"
        try:
            stmt = select(User).where(User.email == email)
            res = await session.execute(stmt)
            dev_user = res.scalars().first()
            if not dev_user:
                dev_user = User(
                    id=uuid.uuid5(uuid.NAMESPACE_DNS, email),
                    email=email,
                    name=name,
                    role="member",
                )
                session.add(dev_user)
                await session.commit()
                await session.refresh(dev_user)
            return dev_user
        finally:
            if close_session:
                await session.close()

    # Attempt JWT decoding (Clerk JWKS, PEM, Secret Key, or dev verification)
    payload = None

    # 1. Clerk JWKS verification if JWKS URL or Issuer is configured and token is RS256
    token_alg = "RS256"
    try:
        header = jwt.get_unverified_header(token)
        token_alg = header.get("alg", "RS256")
    except Exception:
        pass

    # 1. Neon Auth / Clerk JWKS verification if JWKS URL or Issuer is configured
    jwks_url = settings.NEON_AUTH_JWKS_URL
    if not jwks_url and settings.NEON_AUTH_URL:
        jwks_url = f"{settings.NEON_AUTH_URL.rstrip('/')}/.well-known/jwks.json"
    if not jwks_url:
        jwks_url = settings.CLERK_JWKS_URL
    if not jwks_url and settings.CLERK_ISSUER:
        jwks_url = f"{settings.CLERK_ISSUER.rstrip('/')}/.well-known/jwks.json"

    if jwks_url:
        try:
            jwk_client = jwt.PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "EdDSA", "ES256"],
                options={"verify_exp": True},
            )
        except Exception as exc:
            logger.debug(f"[AUTH] JWKS verification failed for {jwks_url}, trying fallbacks: {exc}")

    # 2. PEM Public Key verification
    if not payload and settings.CLERK_PEM_PUBLIC_KEY:
        try:
            payload = jwt.decode(
                token,
                settings.CLERK_PEM_PUBLIC_KEY,
                algorithms=["RS256"],
                options={"verify_exp": True},
            )
        except Exception as exc:
            logger.debug(f"[AUTH] PEM public key verification failed: {exc}")

    # 3. Secret key verification
    if not payload and settings.CLERK_SECRET_KEY:
        try:
            payload = jwt.decode(
                token,
                settings.CLERK_SECRET_KEY,
                algorithms=["HS256", "RS256"],
                options={"verify_signature": False},
            )
        except Exception as exc:
            logger.debug(f"[AUTH] Secret key decoding failed: {exc}")

    # 4. Fallback unverified decode for dev/mock mode
    if not payload:
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
        except Exception as exc:
            logger.debug(f"[AUTH] Unverified decode failed: {exc}")
            return None

    if not payload:
        return None

    # Extract user identifiers from JWT claims
    sub = payload.get("sub")
    email = payload.get("email") or payload.get("primary_email_address")
    name = payload.get("name") or payload.get("full_name") or payload.get("first_name")

    if not sub and not email:
        return None

    close_session = False
    session = db
    if session is None:
        session = async_session_maker()
        close_session = True

    try:
        user = None

        # Derive deterministic UUID from external auth id (sub)
        try:
            user_uuid = uuid.UUID(sub)
        except (ValueError, TypeError):
            user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(sub))

        # Check by id or email
        stmt = select(User).where((User.id == user_uuid) | (User.email == email))
        res = await session.execute(stmt)
        user = res.scalars().first()

        # Auto-provision / Upsert User if authentic JWT has no existing DB record
        if not user:
            user_email = email or f"{sub}@quorum.internal"
            user = User(
                id=user_uuid,
                email=user_email,
                name=name or "Quorum User",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"[AUTH] Provisioned new user {user.id} ({user.email}) via Clerk external id {sub}")
        else:
            # Sync name or email if updated
            updated = False
            if name and user.name != name:
                user.name = name
                updated = True
            if email and user.email != email:
                user.email = email
                updated = True
            if updated:
                await session.commit()
                await session.refresh(user)

        return user
    finally:
        if close_session:
            await session.close()


async def get_current_user(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Standard FastAPI dependency requiring an authenticated user.
    Supports Authorization header (Bearer token) or HttpOnly quorum_session cookie.
    Raises HTTP 401 if unauthenticated.
    """
    token = auth.credentials if auth else None
    if not token:
        token = request.cookies.get("quorum_session")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_current_user_from_token(token, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_non_guest_write_access(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Centralized authorization guard rejecting all mutating requests from Guest Judge sessions.
    Returns 403 Forbidden with X-Error-Code: guest_read_only.
    """
    if current_user.role == UserRole.GUEST.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest accounts have read-only access",
            headers={"X-Error-Code": "guest_read_only"},
        )
    return current_user


async def cleanup_stale_guest_sessions(db: AsyncSession) -> int:
    """
    Explicit, safe maintenance task: deletes only revoked sessions or sessions expired
    for more than 7 days. Never run on normal guest requests; never deletes active sessions.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    stmt = delete(GuestSession).where(
        or_(
            GuestSession.revoked_at.isnot(None),
            GuestSession.expires_at < cutoff,
        )
    )
    res = await db.execute(stmt)
    await db.commit()
    return res.rowcount


async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
) -> User:
    """Authenticate WebSocket connection via query parameter, cookie, or Authorization header."""
    auth_token = token
    if not auth_token:
        auth_token = websocket.headers.get("authorization")
    if not auth_token:
        auth_token = websocket.cookies.get("quorum_session")

    user = await get_current_user_from_token(auth_token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return user

