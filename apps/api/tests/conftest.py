import os
from urllib.parse import urlparse, urlunparse
import pytest
from sqlalchemy import text

# ── 1. Configure test environment BEFORE any application module imports ─────
# Ensure PRODUCTION_DATABASE_URL records the production database reference
orig_db_url = os.environ.get("DATABASE_URL", "")
if orig_db_url and "neondb" in orig_db_url:
    os.environ["PRODUCTION_DATABASE_URL"] = orig_db_url
    parsed = urlparse(orig_db_url)
    test_parsed = parsed._replace(path="/quorum_test")
    test_url = urlunparse(test_parsed)
    os.environ["TEST_DATABASE_URL"] = test_url
    os.environ["DATABASE_URL"] = test_url

os.environ["ENVIRONMENT"] = "test"


@pytest.fixture(scope="session", autouse=True)
def verify_test_environment_isolation():
    """
    Session-wide guardrail assertion:
    Confirms tests execute with ENVIRONMENT=test against the dedicated test database 'quorum_test'.
    Refuses execution if targeting production 'neondb'.
    """
    from src.core.config import settings
    from src.db.session import DATABASE_URL, get_database_fingerprint

    assert settings.ENVIRONMENT.lower() in ("test", "testing"), (
        f"GUARDRAIL REFUSAL: Pytest must run with ENVIRONMENT=test, got '{settings.ENVIRONMENT}'"
    )

    host, dbname = get_database_fingerprint(DATABASE_URL)
    assert dbname != "neondb", (
        f"GUARDRAIL REFUSAL: Tests attempted connection to production database '{dbname}'"
    )
    assert "test" in dbname.lower(), (
        f"GUARDRAIL REFUSAL: Test database name must contain 'test', got '{dbname}'"
    )


@pytest.fixture(autouse=True)
async def cleanup_test_database():
    """
    Per-test cleanup:
    Cleans up test records created in the dedicated quorum_test database so tests
    are strictly isolated and do not pollute the test database.
    """
    yield
    from src.db.session import async_session_maker
    async with async_session_maker() as session:
        try:
            # Clean up in dependency order using CASCADE
            await session.execute(text("TRUNCATE TABLE users CASCADE;"))
            await session.execute(text("TRUNCATE TABLE sources CASCADE;"))
            await session.commit()
        except Exception:
            await session.rollback()
