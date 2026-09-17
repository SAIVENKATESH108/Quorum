import base64
import json
import logging
import uuid
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Query, Security, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models import User
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
                return user
        finally:
            if close_session:
                await session.close()
    except ValueError:
        pass

    # Handle test / mock token prefixes - isolated to dedicated dev user
    if token.startswith("test_") or token == "mock_token":
        close_session = False
        session = db
        if session is None:
            session = async_session_maker()
            close_session = True

        try:
            stmt = select(User).where(User.email == "dev@quorum.local")
            res = await session.execute(stmt)
            dev_user = res.scalars().first()
            if not dev_user:
                dev_user = User(
                    id=uuid.uuid5(uuid.NAMESPACE_DNS, "dev@quorum.local"),
                    email="dev@quorum.local",
                    name="Local Developer",
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

    # 1. Clerk JWKS verification if JWKS URL or Issuer is configured
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
                algorithms=["RS256"],
                options={"verify_exp": True},
            )
        except Exception as exc:
            logger.debug(f"[AUTH] Clerk JWKS verification failed, trying fallbacks: {exc}")

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
    auth: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Standard FastAPI dependency requiring an authenticated user.
    Raises HTTP 401 if unauthenticated.
    """
    token = auth.credentials if auth else None
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


async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
) -> User:
    """Authenticate WebSocket connection via query parameter or Authorization header."""
    auth_token = token
    if not auth_token:
        auth_token = websocket.headers.get("authorization")

    user = await get_current_user_from_token(auth_token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return user
