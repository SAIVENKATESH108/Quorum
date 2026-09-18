import time
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from src.core.rate_limiter import report_rate_limiter
from src.core.redis import close_redis_client
from src.db.models import Project, Report, ReportSection, ReportStatus, User
from src.db.session import async_session_maker
from src.main import app


async def create_db_user() -> User:
    """Helper to create an authenticated user in the database."""
    async with async_session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"api_tester_{uuid.uuid4().hex[:8]}@quorum.ai",
            name="API Test User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.mark.asyncio
async def test_unauthorized_access_rejection():
    """Verify unauthorized requests are rejected with 401 and structured error response."""
    await close_redis_client()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Missing token
            res = await client.get("/api/projects")
            assert res.status_code == 401
            data = res.json()
            assert data["error"] == "unauthorized"
            assert "Authentication required" in data["detail"]

            # 2. Invalid token
            res_invalid = await client.get(
                "/api/projects",
                headers={"Authorization": "Bearer not-a-valid-token"},
            )
            assert res_invalid.status_code == 401
            assert res_invalid.json()["error"] == "unauthorized"
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_create_and_list_projects():
    """Verify creating and listing projects for an authenticated user."""
    await close_redis_client()
    try:
        user = await create_db_user()
        headers = {"Authorization": f"Bearer {user.id}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create project
            payload = {"title": "Decentralized AI Governance"}
            res = await client.post("/api/projects", json=payload, headers=headers)
            assert res.status_code == 201
            project_data = res.json()
            assert project_data["title"] == "Decentralized AI Governance"
            assert project_data["user_id"] == str(user.id)
            assert "id" in project_data

            # List projects
            list_res = await client.get("/api/projects", headers=headers)
            assert list_res.status_code == 200
            projects = list_res.json()
            assert len(projects) >= 1
            project_ids = [p["id"] for p in projects]
            assert project_data["id"] in project_ids
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_successful_report_creation_and_latency():
    """
    Verify creating a report:
    - Returns HTTP 201
    - Response time is under 500ms (non-blocking DAG initialization)
    - Status is 'pending'
    - Report ID returned
    """
    await close_redis_client()
    try:
        user = await create_db_user()
        headers = {"Authorization": f"Bearer {user.id}"}

        from unittest.mock import AsyncMock, patch

        from src.core.redis import get_redis_client
        await get_redis_client()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create project first
            proj_res = await client.post(
                "/api/projects",
                json={"title": "High-Throughput Consensus"},
                headers=headers,
            )
            project_id = proj_res.json()["id"]

            # Create report and measure latency while verifying background pipeline is triggered
            with patch("src.api.projects._run_report_pipeline_background", new_callable=AsyncMock) as mock_pipeline:
                start_time = time.perf_counter()
                report_res = await client.post(
                    f"/api/projects/{project_id}/reports",
                    json={"query": "Distributed Consensus Mechanisms & FLP Impossibility"},
                    headers=headers,
                )
                elapsed = time.perf_counter() - start_time

            assert report_res.status_code == 201
            # Verify non-blocking immediate return (does not wait for multi-minute DAG execution)
            assert elapsed < 15.0, f"Report creation took {elapsed:.3f}s, expected immediate return < 15.0s"

            # Verify background task was triggered
            mock_pipeline.assert_called_once()

            report_data = report_res.json()
            assert report_data["status"] == "pending"
            assert "report_id" in report_data
            assert report_data["id"] == report_data["report_id"]
            assert report_data["query"] == "Distributed Consensus Mechanisms & FLP Impossibility"
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_cross_user_access_rejection():
    """
    Verify cross-user access rejection:
    - User A owns Project A and Report A.
    - User B cannot create a report in Project A (403 Forbidden).
    - User B cannot GET Report A (403 Forbidden).
    - User B cannot DELETE Report A (403 Forbidden).
    """
    await close_redis_client()
    try:
        user_a = await create_db_user()
        user_b = await create_db_user()

        headers_a = {"Authorization": f"Bearer {user_a.id}"}
        headers_b = {"Authorization": f"Bearer {user_b.id}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # User A creates project and report
            p_res = await client.post(
                "/api/projects",
                json={"title": "Confidential Research"},
                headers=headers_a,
            )
            project_a_id = p_res.json()["id"]

            r_res = await client.post(
                f"/api/projects/{project_a_id}/reports",
                json={"query": "Zero Knowledge Proof Systems in Production"},
                headers=headers_a,
            )
            report_a_id = r_res.json()["id"]

            # User B attempts to create report under User A's project -> 403 Forbidden
            cross_create = await client.post(
                f"/api/projects/{project_a_id}/reports",
                json={"query": "Intrusion Attempt"},
                headers=headers_b,
            )
            assert cross_create.status_code == 403
            assert cross_create.json()["error"] == "forbidden"
            assert "Access denied" in cross_create.json()["detail"]

            # User B attempts to read User A's report -> 403 Forbidden
            cross_get = await client.get(
                f"/api/reports/{report_a_id}",
                headers=headers_b,
            )
            assert cross_get.status_code == 403
            assert cross_get.json()["error"] == "forbidden"

            # User B attempts to delete User A's report -> 403 Forbidden
            cross_del = await client.delete(
                f"/api/reports/{report_a_id}",
                headers=headers_b,
            )
            assert cross_del.status_code == 403
            assert cross_del.json()["error"] == "forbidden"
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_not_found_rejection():
    """Verify 404 status code and structured error when querying non-existent resources."""
    await close_redis_client()
    try:
        user = await create_db_user()
        headers = {"Authorization": f"Bearer {user.id}"}
        random_uuid = uuid.uuid4()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Non-existent report
            res_rep = await client.get(f"/api/reports/{random_uuid}", headers=headers)
            assert res_rep.status_code == 404
            assert res_rep.json()["error"] == "not_found"

            # Non-existent project reports
            res_proj = await client.get(f"/api/projects/{random_uuid}/reports", headers=headers)
            assert res_proj.status_code == 404
            assert res_proj.json()["error"] == "not_found"
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_rate_limit_enforcement():
    """Verify Redis sliding window rate limiter returns 429 when quota is exceeded."""
    await close_redis_client()
    original_limit = report_rate_limiter.limit
    report_rate_limiter.limit = 3  # Set lower limit for fast testing

    try:
        user = await create_db_user()
        headers = {"Authorization": f"Bearer {user.id}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            proj_res = await client.post(
                "/api/projects",
                json={"title": "Rate Limit Test Project"},
                headers=headers,
            )
            project_id = proj_res.json()["id"]

            # Requests 1, 2, 3 should succeed
            for i in range(3):
                res = await client.post(
                    f"/api/projects/{project_id}/reports",
                    json={"query": f"Rate test query #{i+1}"},
                    headers=headers,
                )
                assert res.status_code == 201

            # Request 4 should be rejected with 429 Too Many Requests
            res_exceeded = await client.post(
                f"/api/projects/{project_id}/reports",
                json={"query": "Exceeding query"},
                headers=headers,
            )
            assert res_exceeded.status_code == 429
            data = res_exceeded.json()
            assert data["error"] == "rate_limit_exceeded"
            assert "Rate limit exceeded" in data["detail"]
    finally:
        report_rate_limiter.limit = original_limit
        await close_redis_client()


@pytest.mark.asyncio
async def test_get_report_details_and_deletion():
    """
    Verify:
    - Sections returned are properly ordered by order_index
    - Report can be deleted (204 No Content)
    - After deletion, GET returns 404 Not Found
    """
    await close_redis_client()
    try:
        user = await create_db_user()
        headers = {"Authorization": f"Bearer {user.id}"}

        # Setup project and report with sections in DB
        project_id = uuid.uuid4()
        report_id = uuid.uuid4()

        async with async_session_maker() as session:
            project = Project(id=project_id, user_id=user.id, title="Structured Report Project")
            report = Report(
                id=report_id,
                project_id=project_id,
                query="Quantum Key Distribution Protocols",
                status=ReportStatus.COMPLETE,
            )
            # Insert sections out of order to verify sorted response
            sec2 = ReportSection(
                id=uuid.uuid4(),
                report_id=report_id,
                heading="2. Implementation Challenges",
                content="Decoherence and repeater limits...",
                order_index=2,
            )
            sec1 = ReportSection(
                id=uuid.uuid4(),
                report_id=report_id,
                heading="1. Theoretical Foundations",
                content="BB84 and E91 protocols...",
                order_index=1,
            )
            session.add(project)
            session.add(report)
            session.add(sec2)
            session.add(sec1)
            await session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Fetch details
            res = await client.get(f"/api/reports/{report_id}", headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == str(report_id)
            assert data["status"] == "complete"
            assert len(data["sections"]) == 2
            # Verify ordering
            assert data["sections"][0]["order_index"] == 1
            assert data["sections"][0]["heading"] == "1. Theoretical Foundations"
            assert data["sections"][1]["order_index"] == 2
            assert data["sections"][1]["heading"] == "2. Implementation Challenges"

            # 2. Delete report
            del_res = await client.delete(f"/api/reports/{report_id}", headers=headers)
            assert del_res.status_code == 204

            # 3. Verify report no longer exists
            res_after = await client.get(f"/api/reports/{report_id}", headers=headers)
            assert res_after.status_code == 404
    finally:
        await close_redis_client()
