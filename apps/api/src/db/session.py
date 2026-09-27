import os
import logging
from typing import AsyncGenerator, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings

logger = logging.getLogger("quorum.db")


def get_database_fingerprint(url: str) -> Tuple[str, str]:
    """
    Extract safe database host and database name fingerprint without exposing credentials.
    Returns (host, dbname).
    """
    if not url:
        return ("none", "none")
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    dbname = parsed.path.lstrip("/") or "none"
    return (host.lower(), dbname.lower())


def get_async_database_url() -> str:
    """
    Format DATABASE_URL to use asyncpg driver, strictly enforcing environment separation.
    """
    is_test = settings.ENVIRONMENT.lower() in ("test", "testing")

    if is_test:
        url = settings.TEST_DATABASE_URL or os.environ.get("TEST_DATABASE_URL")
        if not url and settings.DATABASE_URL:
            # Fall back to quorum_test on the configured cluster
            parsed = urlparse(settings.DATABASE_URL)
            test_parsed = parsed._replace(path="/quorum_test")
            url = urlunparse(test_parsed)
        if not url:
            url = "postgresql+asyncpg://postgres:postgres@localhost:5432/quorum_test"
    else:
        url = settings.DATABASE_URL or "postgresql+asyncpg://postgres:postgres@localhost:5432/quorum"

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return url


def validate_database_guardrails(active_url: str) -> None:
    """
    Explicit environment guardrails:
    1. Test execution must require ENVIRONMENT=test.
    2. Test database URL must be distinct from production URL.
    3. Refuse to run test fixtures when ENVIRONMENT=production.
    4. Assert test database host/name fingerprint does not equal production database fingerprint.
    5. Do not log raw database URLs.
    """
    is_test = settings.ENVIRONMENT.lower() in ("test", "testing")
    is_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
    active_host, active_db = get_database_fingerprint(active_url)

    prod_ref = os.environ.get("PRODUCTION_DATABASE_URL") or settings.DATABASE_URL or ""
    prod_host, prod_db = get_database_fingerprint(prod_ref) if prod_ref else ("none", "none")

    # Guardrail 1: Disallow pytest from running in production mode
    if is_pytest and not is_test:
        raise RuntimeError(
            f"GUARDRAIL REFUSAL: Pytest execution detected with ENVIRONMENT='{settings.ENVIRONMENT}'. "
            "Tests must strictly run with ENVIRONMENT=test and an isolated test database."
        )

    # Guardrail 2: Test environment must never target the production database
    if is_test:
        if active_db in ("neondb", "production", "prod") and "test" not in active_db:
            raise RuntimeError(
                f"GUARDRAIL REFUSAL: Test environment attempted connection to production database '{active_db}'. "
                "Tests MUST use a distinct test database (e.g. quorum_test)."
            )
        if prod_ref and prod_db in ("neondb", "production") and (active_host, active_db) == (prod_host, prod_db):
            raise RuntimeError(
                f"GUARDRAIL REFUSAL: Test database fingerprint ({active_host}/{active_db}) "
                f"matches production database fingerprint ({prod_host}/{prod_db}). Execution aborted."
            )


DATABASE_URL = get_async_database_url()
validate_database_guardrails(DATABASE_URL)

# Handle asyncpg ssl argument and remove unsupported query parameters
connect_args = {}
parsed = urlparse(DATABASE_URL)
if parsed.query:
    qs = parse_qs(parsed.query)
    if "sslmode" in qs:
        sslmode = qs.pop("sslmode")[0]
        if sslmode in ("require", "verify-ca", "verify-full"):
            connect_args["ssl"] = "require"
    # asyncpg does not accept channel_binding or endpoint parameters
    qs.pop("channel_binding", None)
    qs.pop("endpoint", None)
    new_query = urlencode(qs, doseq=True)
    DATABASE_URL = urlunparse(parsed._replace(query=new_query))

if "-pooler" in DATABASE_URL:
    connect_args["statement_cache_size"] = 0

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
    poolclass=pool.NullPool,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for yielding an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
