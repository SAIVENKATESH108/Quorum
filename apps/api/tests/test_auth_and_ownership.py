import uuid
from unittest.mock import AsyncMock, patch
import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from src.core.redis import close_redis_client
from src.core.security import get_current_user_from_token
from src.db.models import User
from src.db.session import async_session_maker
from src.main import app

DEV_SECRET = "super-secret-key-for-jwt-signing-with-at-least-32-bytes"


def generate_clerk_mock_jwt(sub: str, email: str, name: str) -> str:
    """Generate a JWT simulating Clerk's session token payload."""
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "iss": "https://clerk.quorum.ai",
        "aud": "quorum-api",
        "iat": 1700000000,
        "exp": 2000000000,
    }
    return jwt.encode(payload, DEV_SECRET, algorithm="HS256")


@pytest.mark.asyncio
async def test_clerk_jwt_auto_provisioning():
    """Verify Clerk-issued JWT triggers auto-provisioning/upsert in the users table."""
    clerk_sub = f"user_clerk_{uuid.uuid4().hex[:10]}"
    clerk_email = f"clerk_{uuid.uuid4().hex[:8]}@quorum.ai"
    clerk_name = "Clerk Verified Tester"

    token = generate_clerk_mock_jwt(clerk_sub, clerk_email, clerk_name)

    async with async_session_maker() as session:
        # First sign-in: User does not exist yet
        user = await get_current_user_from_token(token, db=session)
        assert user is not None
        assert user.email == clerk_email
        assert user.name == clerk_name

        # Verify persisted in database with deterministic UUID from external auth id
        expected_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(clerk_sub))
        assert user.id == expected_uuid

        # Second sign-in with updated name: Upsert / syncs data without duplicate error
        updated_token = generate_clerk_mock_jwt(clerk_sub, clerk_email, "Clerk Updated Name")
        user_again = await get_current_user_from_token(updated_token, db=session)
        assert user_again.id == user.id
        assert user_again.name == "Clerk Updated Name"


@pytest.mark.asyncio
async def test_strict_user_ownership_isolation():
    """
    Test complete ownership verification end-to-end:
    - User A creates Project A and Report A.
    - User B authenticates as a distinct user.
    - User B cannot view Project A.
    - User B cannot list reports for Project A.
    - User B cannot view Report A.
    - User B cannot create reports under Project A.
    - User B cannot delete Report A.
    - User B cannot stream WebSocket updates for Report A.
    """
    from src.core.redis import get_redis_client
    await get_redis_client()

    try:
        # 1. Setup User A via Clerk JWT
        user_a_sub = f"user_a_{uuid.uuid4().hex[:8]}"
        user_a_token = generate_clerk_mock_jwt(user_a_sub, f"{user_a_sub}@quorum.ai", "User A")
        headers_a = {"Authorization": f"Bearer {user_a_token}"}

        # 2. Setup User B via Clerk JWT
        user_b_sub = f"user_b_{uuid.uuid4().hex[:8]}"
        user_b_token = generate_clerk_mock_jwt(user_b_sub, f"{user_b_sub}@quorum.ai", "User B")
        headers_b = {"Authorization": f"Bearer {user_b_token}"}

        # Patch background execution to keep test instant and decoupled from external AI APIs
        with (
            patch("src.api.projects._run_report_pipeline_background", new_callable=AsyncMock),
            patch("src.agents.engine.OrchestrationEngine.run_report", new_callable=AsyncMock),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # User A creates Project A
                res_p = await client.post(
                    "/api/projects",
                    headers=headers_a,
                    json={"title": "User A Private Workspace"},
                )
                assert res_p.status_code == 201
                project_a = res_p.json()
                project_a_id = project_a["id"]

                # User A creates Report A
                res_r = await client.post(
                    f"/api/projects/{project_a_id}/reports",
                    headers=headers_a,
                    json={"query": "Confidential research by User A"},
                )
                assert res_r.status_code == 201
                report_a = res_r.json()
                report_a_id = report_a["report_id"]

                # User A can view Report A
                res_get_a = await client.get(f"/api/reports/{report_a_id}", headers=headers_a)
                assert res_get_a.status_code == 200
                assert res_get_a.json()["id"] == report_a_id

                # --- USER B ATTEMPTS UNAUTHORIZED ACCESS ---

                # User B attempts to access Project A's reports list -> 403 Forbidden
                res_b_list = await client.get(
                    f"/api/projects/{project_a_id}/reports",
                    headers=headers_b,
                )
                assert res_b_list.status_code == 403
                assert "Access denied" in res_b_list.json()["detail"]

                # User B attempts to view Report A directly -> 403 Forbidden
                res_b_rep = await client.get(
                    f"/api/reports/{report_a_id}",
                    headers=headers_b,
                )
                assert res_b_rep.status_code == 403
                assert "Access denied" in res_b_rep.json()["detail"]

                # User B attempts to create report in User A's project -> 403 Forbidden
                res_b_create = await client.post(
                    f"/api/projects/{project_a_id}/reports",
                    headers=headers_b,
                    json={"query": "Malicious intrusion attempt"},
                )
                assert res_b_create.status_code == 403
                assert "Access denied" in res_b_create.json()["detail"]

                # User B attempts to delete User A's report -> 403 Forbidden
                res_b_del = await client.delete(
                    f"/api/reports/{report_a_id}",
                    headers=headers_b,
                )
                assert res_b_del.status_code == 403
                assert "Access denied" in res_b_del.json()["detail"]

                # 3. Test WebSocket Isolation: User B cannot stream User A's report WebSocket
                from src.api.websocket import stream_report_status

                class MockWS:
                    def __init__(self):
                        self.accepted = False
                        self.closed = False
                        self.close_code = None

                    async def accept(self):
                        self.accepted = True

                    async def send_json(self, data):
                        pass

                    async def close(self, code=1000, reason=None):
                        self.closed = True
                        self.close_code = code

                unauth_ws = MockWS()
                user_b_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(user_b_sub))
                await stream_report_status(
                    websocket=unauth_ws,
                    report_id=uuid.UUID(report_a_id),
                    current_user=User(id=user_b_uuid, email=f"{user_b_sub}@quorum.ai"),
                )
                assert unauth_ws.closed is True
                assert unauth_ws.close_code == 1008
                assert unauth_ws.accepted is False

                # 4. User A can safely delete Report A
                res_a_del = await client.delete(
                    f"/api/reports/{report_a_id}",
                    headers=headers_a,
                )
                assert res_a_del.status_code == 204
    finally:
        await close_redis_client()
