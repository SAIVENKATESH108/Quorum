from typing import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings


def get_async_database_url() -> str:
    """Format DATABASE_URL to use asyncpg driver."""
    url = settings.DATABASE_URL or "postgresql+asyncpg://postgres:postgres@localhost:5432/quorum"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL = get_async_database_url()

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

from sqlalchemy import pool

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
