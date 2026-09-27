import os
import uuid
import datetime
from datetime import datetime as dt, timezone, timedelta
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

import jwt
from src.core.config import settings
from src.core.redis import close_redis_client
from src.core.security import cleanup_stale_guest_sessions
from src.db.models import Project, Report, ReportSection, ReportSource, ReportStatus, Source, User, GuestSession
from src.db.session import async_session_maker
from src.main import app


async def create_test_user(role: str = "member", email_prefix: str = "user") -> User:
    """Helper to create a test user with a given role."""
    async with async_session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"{email_prefix}_{uuid.uuid4().hex[:8]}@quorum.ai",
            name=f"Test {role.capitalize()}",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.mark.asyncio
async def test_guest_session_creation_cookie_and_token_free_body():
    """
    1. POST /api/auth/guest:
    - Sets HttpOnly quorum_session cookie.
    - Body returns token-free metadata: success, session_type, role, expires_at.
    - Body must NOT expose raw access_token or token string.
    - Creates a corresponding GuestSession row with unique jti.
    """
    await close_redis_client()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/auth/guest")
            assert res.status_code == 200
            data = res.json()

            # Safe token-free body verification
            assert data["success"] is True
            assert data["session_type"] == "guest"
            assert data["role"] == "guest"
            assert "expires_at" in data
            assert "access_token" not in data
            assert "token" not in data
            assert "jwt" not in data

            # Cookie verification
            cookies = res.cookies
            assert "quorum_session" in cookies
            cookie_header = res.headers.get("set-cookie", "")
            assert "quorum_session=" in cookie_header
            assert "HttpOnly" in cookie_header or "httponly" in cookie_header.lower()
            assert "SameSite=lax" in cookie_header or "samesite=lax" in cookie_header.lower()

            # Verify persisted in database
            async with async_session_maker() as session:
                sessions_res = await session.execute(
                    select(GuestSession).order_by(GuestSession.issued_at.desc()).limit(1)
                )
                latest_session = sessions_res.scalar_one_or_none()
                assert latest_session is not None
                assert latest_session.session_type == "guest"
                assert latest_session.revoked_at is None
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_two_way_role_verification_and_tamper_rejection():
    """
    2. Two-way validation:
    - Token claims role='guest' but points to DB user with role='member' -> rejected 401.
    - Fabricated jti not in guest_sessions table -> rejected 401.
    - Client header role spoofing ignored.
    """
    await close_redis_client()
    try:
        # Create non-guest user
        member = await create_test_user(role="member", email_prefix="spoof")

        # Forge token claiming role=guest for non-guest user
        forged_jti = str(uuid.uuid4())
        secret = settings.AUTH_SECRET_KEY or "local-only-change-this-auth-secret"
        forged_claims = {
            "sub": str(member.id),
            "role": "guest",
            "jti": forged_jti,
            "iat": int(dt.now(timezone.utc).timestamp()),
            "exp": int((dt.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }
        forged_token = jwt.encode(forged_claims, secret, algorithm="HS256")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("quorum_session", forged_token)
            res = await client.get("/api/projects")
            # Must be rejected because DB role is 'member', not 'guest'
            assert res.status_code == 401
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_concurrent_guest_sessions_and_isolated_revocation():
    """
    3. Concurrent Guest Sessions and Per-Session Revocation:
    - Session A and Session B both created.
    - Both can query demo resources.
    - Session A logs out -> only Session A is revoked.
    - Session B remains fully valid and active.
    - Replaying Session A yields 401.
    """
    await close_redis_client()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client_a:
            async with AsyncClient(transport=transport, base_url="http://test") as client_b:
                # 1. Start Session A
                res_a = await client_a.post("/api/auth/guest")
                assert res_a.status_code == 200
                cookie_a = client_a.cookies.get("quorum_session")

                # 2. Start Session B
                res_b = await client_b.post("/api/auth/guest")
                assert res_b.status_code == 200
                cookie_b = client_b.cookies.get("quorum_session")

                # Tokens must have different JTIs
                assert cookie_a != cookie_b

                # Both sessions can access /api/projects
                res_projects_a = await client_a.get("/api/projects")
                assert res_projects_a.status_code == 200

                res_projects_b = await client_b.get("/api/projects")
                assert res_projects_b.status_code == 200

                # 3. Logout Session A
                res_logout_a = await client_a.post("/api/auth/logout")
                assert res_logout_a.status_code == 200
                logout_data = res_logout_a.json()
                assert logout_data["success"] is True

                # 4. Verify Session B remains fully valid
                res_projects_b_after = await client_b.get("/api/projects")
                assert res_projects_b_after.status_code == 200

                # 5. Verify replayed Session A is rejected with 401
                client_replay = AsyncClient(transport=transport, base_url="http://test")
                client_replay.cookies.set("quorum_session", cookie_a)
                res_replay = await client_replay.get("/api/projects")
                assert res_replay.status_code == 401
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_idempotent_logout():
    """
    4. Logout Idempotency:
    - Logout with no cookie returns 200.
    - Logout with already revoked session returns 200.
    """
    await close_redis_client()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # No cookie
            res1 = await client.post("/api/auth/logout")
            assert res1.status_code == 200
            assert res1.json()["success"] is True

            # With guest cookie
            await client.post("/api/auth/guest")
            res2 = await client.post("/api/auth/logout")
            assert res2.status_code == 200
            assert res2.json()["success"] is True

            # Immediately repeating logout
            res3 = await client.post("/api/auth/logout")
            assert res3.status_code == 200
            assert res3.json()["success"] is True
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_curated_demo_visibility_hierarchy():
    """
    5. Curated Demo Visibility Hierarchy:
    - Project 1 (is_guest_demo=True) with Report 1 (is_guest_demo=True) -> VISIBLE
    - Project 2 (is_guest_demo=False) with Report 2 (is_guest_demo=True) -> HIDDEN (parent not demo)
    - Project 3 (is_guest_demo=False) with Report 3 (is_guest_demo=False) -> HIDDEN (private)
    """
    await close_redis_client()
    try:
        admin = await create_test_user(role="admin", email_prefix="admin_vis")

        p1_id = uuid.uuid4()
        r1_id = uuid.uuid4()
        p2_id = uuid.uuid4()
        r2_id = uuid.uuid4()
        p3_id = uuid.uuid4()
        r3_id = uuid.uuid4()

        async with async_session_maker() as session:
            # Curated demo project & report
            p1 = Project(id=p1_id, user_id=admin.id, title="Demo Curated Project", is_guest_demo=True)
            r1 = Report(id=r1_id, project_id=p1_id, status=ReportStatus.COMPLETE, query="Demo Brief", is_guest_demo=True)

            # Orphaned demo flag (parent is private)
            p2 = Project(id=p2_id, user_id=admin.id, title="Private Parent Project", is_guest_demo=False)
            r2 = Report(id=r2_id, project_id=p2_id, status=ReportStatus.COMPLETE, query="Orphaned Demo Report", is_guest_demo=True)

            # Fully private
            p3 = Project(id=p3_id, user_id=admin.id, title="Private Secret Project", is_guest_demo=False)
            r3 = Report(id=r3_id, project_id=p3_id, status=ReportStatus.COMPLETE, query="Private Brief", is_guest_demo=False)

            session.add_all([p1, r1, p2, r2, p3, r3])
            await session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/auth/guest")

            # 1. Projects listing: only p1 visible
            res_p = await client.get("/api/projects")
            assert res_p.status_code == 200
            p_ids = [p["id"] for p in res_p.json()]
            assert str(p1_id) in p_ids
            assert str(p2_id) not in p_ids
            assert str(p3_id) not in p_ids

            # 2. Reports listing: only r1 visible
            res_r = await client.get("/api/reports")
            rep_data = res_r.json()
            r_items = rep_data["items"] if isinstance(rep_data, dict) and "items" in rep_data else rep_data
            r_ids = [r["id"] for r in r_items]
            assert str(r1_id) in r_ids
            assert str(r2_id) not in r_ids
            assert str(r3_id) not in r_ids

            # 3. Direct GET access
            assert (await client.get(f"/api/projects/{p1_id}")).status_code == 200
            assert (await client.get(f"/api/projects/{p2_id}")).status_code == 403
            assert (await client.get(f"/api/projects/{p3_id}")).status_code == 403

            assert (await client.get(f"/api/reports/{r1_id}")).status_code == 200
            assert (await client.get(f"/api/reports/{r2_id}")).status_code == 403
            assert (await client.get(f"/api/reports/{r3_id}")).status_code == 403
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_admin_curation_endpoint_and_allowlist():
    """
    6. Admin Curation:
    - PATCH /api/admin/curate/{resource_type}/{resource_id}
    - Allowlisted resource types: project, report.
    - Non-allowlisted types (e.g. user, source) return 400.
    - Non-admin callers return 403.
    """
    await close_redis_client()
    try:
        admin = await create_test_user(role="admin", email_prefix="curator_admin")
        member = await create_test_user(role="member", email_prefix="regular_user")

        p_id = uuid.uuid4()
        async with async_session_maker() as session:
            p = Project(id=p_id, user_id=member.id, title="User Work", is_guest_demo=False)
            session.add(p)
            await session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            admin_headers = {"Authorization": f"Bearer {admin.id}"}
            member_headers = {"Authorization": f"Bearer {member.id}"}

            # Member attempt -> 403
            res_mem = await client.patch(
                f"/api/admin/curate/project/{p_id}",
                json={"is_guest_demo": True},
                headers=member_headers,
            )
            assert res_mem.status_code == 403

            # Invalid resource_type -> 400
            res_inv = await client.patch(
                f"/api/admin/curate/invalid_type/{p_id}",
                json={"is_guest_demo": True},
                headers=admin_headers,
            )
            assert res_inv.status_code == 400
            assert "Invalid resource_type" in res_inv.json()["detail"]

            # Admin curation of project -> 200
            res_curate = await client.patch(
                f"/api/admin/curate/project/{p_id}",
                json={"is_guest_demo": True},
                headers=admin_headers,
            )
            assert res_curate.status_code == 200
            assert res_curate.json()["is_guest_demo"] is True

            # Verify in DB
            async with async_session_maker() as session:
                p_db = (await session.execute(select(Project).where(Project.id == p_id))).scalar_one()
                assert p_db.is_guest_demo is True
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_standard_api_payloads_cannot_set_is_guest_demo():
    """
    7. Standard Create/Update payloads cannot toggle is_guest_demo:
    A user posting is_guest_demo=True in /api/projects gets a project with is_guest_demo=False.
    """
    await close_redis_client()
    try:
        user = await create_test_user(role="member", email_prefix="normal_dev")
        headers = {"Authorization": f"Bearer {user.id}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/projects",
                json={"title": "Hacker Attempt", "is_guest_demo": True},
                headers=headers,
            )
            assert res.status_code == 201
            p_data = res.json()
            assert p_data["is_guest_demo"] is False
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_guest_centralized_read_only_rejection():
    """
    8. Centralized Write Guard:
    All write/mutation attempts from a guest session return 403 with code='guest_read_only'.
    """
    await close_redis_client()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/auth/guest")

            # 1. Project creation
            res_p = await client.post("/api/projects", json={"title": "Guest Attempt"})
            assert res_p.status_code == 403
            assert res_p.headers.get("x-error-code") == "guest_read_only" or "Guest accounts have read-only access" in res_p.json().get("detail", "")

            # 2. Report creation
            res_r = await client.post(f"/api/projects/{uuid.uuid4()}/reports", json={"query": "Guest Report"})
            assert res_r.status_code == 403
            assert res_r.headers.get("x-error-code") == "guest_read_only" or "Guest accounts have read-only access" in res_r.json().get("detail", "")

            # 3. Report deletion
            res_d = await client.delete(f"/api/reports/{uuid.uuid4()}")
            assert res_d.status_code == 403
            assert res_d.headers.get("x-error-code") == "guest_read_only" or "Guest accounts have read-only access" in res_d.json().get("detail", "")

            # 4. Research generation
            res_plan = await client.post("/api/research-jobs", json={"report_id": str(uuid.uuid4()), "topic": "Quantum", "target_venue": "Nature"})
            assert res_plan.status_code == 403
            assert res_plan.headers.get("x-error-code") == "guest_read_only" or "Guest accounts have read-only access" in res_plan.json().get("detail", "")
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_diagnostics_masks_database_host():
    """
    9. Admin diagnostics must return sha256 prefix and label, NOT raw database host.
    """
    await close_redis_client()
    try:
        admin = await create_test_user(role="admin", email_prefix="admin_diag")
        admin_headers = {"Authorization": f"Bearer {admin.id}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/admin/diagnostics", headers=admin_headers)
            assert res.status_code == 200
            data = res.json()
            assert "safe_db_host_fingerprint" in data
            assert data["safe_db_host_fingerprint"].startswith("sha256:")
            assert len(data["safe_db_host_fingerprint"]) <= 20
            assert "db_host_label" in data
            # Ensure raw host like ep-*.aws.neon.tech is never returned
            assert "neon.tech" not in data["safe_db_host_fingerprint"]
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_guest_session_cleanup_maintenance_task():
    """
    10. Stale Guest Session Cleanup:
    - Active unexpired session is preserved.
    - Revoked session is deleted.
    - Session expired >7 days ago is deleted.
    - Session expired 1 day ago is preserved (until 7-day grace period passes).
    """
    await close_redis_client()
    try:
        now = dt.now(timezone.utc)
        async with async_session_maker() as session:
            # Find judge user
            user_res = await session.execute(select(User).where(User.role == "guest"))
            judge_user = user_res.scalars().first()
            if not judge_user:
                judge_user = await create_test_user(role="guest", email_prefix="judge")

            # 1. Active session
            active_s = GuestSession(
                id=uuid.uuid4(),
                user_id=judge_user.id,
                session_type="guest",
                issued_at=now,
                expires_at=now + timedelta(hours=2),
                revoked_at=None,
            )
            # 2. Revoked session
            revoked_s = GuestSession(
                id=uuid.uuid4(),
                user_id=judge_user.id,
                session_type="guest",
                issued_at=now - timedelta(days=1),
                expires_at=now + timedelta(hours=1),
                revoked_at=now - timedelta(hours=2),
            )
            # 3. Expired >7 days ago
            old_expired_s = GuestSession(
                id=uuid.uuid4(),
                user_id=judge_user.id,
                session_type="guest",
                issued_at=now - timedelta(days=10),
                expires_at=now - timedelta(days=8),
                revoked_at=None,
            )
            # 4. Expired 2 days ago (<7 days)
            recent_expired_s = GuestSession(
                id=uuid.uuid4(),
                user_id=judge_user.id,
                session_type="guest",
                issued_at=now - timedelta(days=3),
                expires_at=now - timedelta(days=2),
                revoked_at=None,
            )

            session.add_all([active_s, revoked_s, old_expired_s, recent_expired_s])
            await session.commit()

            # Run maintenance cleanup
            deleted_count = await cleanup_stale_guest_sessions(session)
            await session.commit()

            # Active & recent expired (<7d) must still exist
            active_check = (await session.execute(select(GuestSession).where(GuestSession.id == active_s.id))).scalar_one_or_none()
            assert active_check is not None

            recent_check = (await session.execute(select(GuestSession).where(GuestSession.id == recent_expired_s.id))).scalar_one_or_none()
            assert recent_check is not None

            # Revoked & old expired must be deleted
            revoked_check = (await session.execute(select(GuestSession).where(GuestSession.id == revoked_s.id))).scalar_one_or_none()
            assert revoked_check is None

            old_check = (await session.execute(select(GuestSession).where(GuestSession.id == old_expired_s.id))).scalar_one_or_none()
            assert old_check is None
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_anonymous_and_guest_private_report_isolation():
    """
    11. Anonymous & Guest isolation on private reports:
    - Anonymous requesting private report -> 401 Unauthorized
    - Guest requesting private report -> 403 Forbidden
    - Anonymous requesting demo report -> 200 OK (public showcase)
    - Guest requesting demo report -> 200 OK
    """
    await close_redis_client()
    try:
        owner = await create_test_user(role="member", email_prefix="report_owner")

        demo_p_id = uuid.uuid4()
        demo_r_id = uuid.uuid4()
        priv_p_id = uuid.uuid4()
        priv_r_id = uuid.uuid4()

        async with async_session_maker() as session:
            # Curated demo project and report
            dp = Project(id=demo_p_id, user_id=owner.id, title="Public Demo Project", is_guest_demo=True)
            dr = Report(id=demo_r_id, project_id=demo_p_id, status=ReportStatus.COMPLETE, query="Public Brief", is_guest_demo=True)

            # Private project and report
            pp = Project(id=priv_p_id, user_id=owner.id, title="Secret Project", is_guest_demo=False)
            pr = Report(id=priv_r_id, project_id=priv_p_id, status=ReportStatus.COMPLETE, query="Secret Brief", is_guest_demo=False)

            session.add_all([dp, dr, pp, pr])
            await session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Anonymous to private report -> 401
            res_anon_priv = await client.get(f"/api/reports/{priv_r_id}")
            assert res_anon_priv.status_code == 401

            # 2. Anonymous to demo report -> 200 OK
            res_anon_demo = await client.get(f"/api/reports/{demo_r_id}")
            assert res_anon_demo.status_code == 200
            assert res_anon_demo.json()["id"] == str(demo_r_id)

            # 3. Guest Judge login
            await client.post("/api/auth/guest")

            # 4. Guest to private report -> 403 Forbidden
            res_guest_priv = await client.get(f"/api/reports/{priv_r_id}")
            assert res_guest_priv.status_code == 403

            # 5. Guest to demo report -> 200 OK
            res_guest_demo = await client.get(f"/api/reports/{demo_r_id}")
            assert res_guest_demo.status_code == 200
            assert res_guest_demo.json()["id"] == str(demo_r_id)
    finally:
        await close_redis_client()

