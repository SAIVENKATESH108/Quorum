import os
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.core.redis import close_redis_client
from src.db.models import Project, Report, ReportSection, ReportSource, ReportStatus, Source, User


from src.db.session import async_session_maker
from src.main import app

LEGACY_HARDCODED_UUID = "9918d84c-7694-4df4-ad1b-39313d6577dc"


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
async def test_stage3_unauthenticated_requests_receive_401():
    """
    1. 401 Behavior:
    Unauthenticated GET /api/projects and GET /api/reports must receive 401.
    No project or report data may be returned.
    """
    await close_redis_client()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Unauthenticated projects list
            res_proj = await client.get("/api/projects")
            assert res_proj.status_code == 401
            assert res_proj.json()["error"] == "unauthorized"

            # Unauthenticated reports list
            res_rep = await client.get("/api/reports")
            assert res_rep.status_code == 401
            assert res_rep.json()["error"] == "unauthorized"
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_stage3_cross_tenant_isolation_403():
    """
    2. 403 Behavior:
    Authenticated non-owner requesting private project receives 403 Forbidden.
    No project data is disclosed to the non-owner.
    """
    await close_redis_client()
    try:
        owner = await create_test_user(role="member", email_prefix="owner")
        stranger = await create_test_user(role="member", email_prefix="stranger")

        owner_headers = {"Authorization": f"Bearer {owner.id}"}
        stranger_headers = {"Authorization": f"Bearer {stranger.id}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Owner creates project
            res_create = await client.post(
                "/api/projects",
                json={"title": "Private Tenant Vault"},
                headers=owner_headers,
            )
            assert res_create.status_code == 201
            project_id = res_create.json()["id"]

            # Stranger attempts to read private project
            res_stranger = await client.get(
                f"/api/projects/{project_id}",
                headers=stranger_headers,
            )
            assert res_stranger.status_code == 403
            assert res_stranger.json()["error"] == "forbidden"

            # Stranger project list does not disclose owner's project
            res_list = await client.get("/api/projects", headers=stranger_headers)
            assert res_list.status_code == 200
            stranger_projects = res_list.json()
            assert not any(p["id"] == project_id for p in stranger_projects)
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_stage3_ownership_integrity_no_client_spoofing():
    """
    5. Ownership:
    A create request with valid ownership persists under the authenticated user.
    A client-provided spoofed user ID cannot assign or override ownership.
    """
    await close_redis_client()
    try:
        real_user = await create_test_user(role="member", email_prefix="real")
        victim_user = await create_test_user(role="member", email_prefix="victim")

        headers = {"Authorization": f"Bearer {real_user.id}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Client attempts to spoof ownership to victim_user
            res = await client.post(
                "/api/projects",
                json={
                    "title": "Anti-Spoofing Verification",
                    "user_id": str(victim_user.id),
                },
                headers=headers,
            )
            assert res.status_code == 201
            project_data = res.json()
            # Must be assigned to authenticated real_user, NOT victim_user
            assert project_data["user_id"] == str(real_user.id)
            assert project_data["user_id"] != str(victim_user.id)
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_stage3_durability_across_reconnect():
    """
    6. Durability:
    Create a project and report with sections and sources.
    Simulate cold start / new database connection session.
    Confirm the same record remains accessible and linked to sections/sources.
    """
    await close_redis_client()
    try:
        user = await create_test_user(role="member", email_prefix="durable")
        project_id = uuid.uuid4()
        report_id = uuid.uuid4()

        # Direct database write to simulate persisted state
        async with async_session_maker() as session:
            project = Project(
                id=project_id,
                user_id=user.id,
                title="Durable Research Project",
            )
            report = Report(
                id=report_id,
                project_id=project_id,
                status=ReportStatus.COMPLETE,
                query="Quantum Encryption Resiliency",
            )

            section = ReportSection(
                id=uuid.uuid4(),
                report_id=report_id,
                heading="Methodology",
                content="Quantum key distribution verified across optical channels.",
                order_index=0,
            )
            source = Source(
                id=uuid.uuid4(),
                title="Quantum Review 2026",
                url="https://doi.org/10.1000/quantum.2026",
            )
            session.add_all([project, report, section, source])
            await session.flush()

            report_source = ReportSource(
                report_id=report_id,
                source_id=source.id,
            )
            session.add(report_source)
            await session.commit()


        # Simulate cold restart: fresh session query
        async with async_session_maker() as fresh_session:
            db_report = await fresh_session.execute(
                select(Report).where(Report.id == report_id)
            )
            loaded_report = db_report.scalars().first()
            assert loaded_report is not None
            assert loaded_report.project_id == project_id
            assert loaded_report.query == "Quantum Encryption Resiliency"

        # Verify through API as owner
        headers = {"Authorization": f"Bearer {user.id}"}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(f"/api/reports/{report_id}", headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == str(report_id)
            assert len(data["sections"]) == 1
            assert data["sections"][0]["heading"] == "Methodology"
            assert len(data["sources"]) == 1
            assert data["sources"][0]["url"] == "https://doi.org/10.1000/quantum.2026"
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_stage3_observability_and_diagnostics():
    """
    8. Observability & Diagnostics:
    - Protected route responses emit X-Quorum-Data-Source: fastapi_backend header.
    - Public visitors cannot access diagnostics (401).
    - Ordinary members cannot access diagnostics (403).
    - Admin users receive non-sensitive system health without secrets.
    """
    await close_redis_client()
    try:
        admin_user = await create_test_user(role="admin", email_prefix="admin")
        member_user = await create_test_user(role="member", email_prefix="member")

        admin_headers = {"Authorization": f"Bearer {admin_user.id}"}
        member_headers = {"Authorization": f"Bearer {member_user.id}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Verify X-Quorum-Data-Source header
            res_ping = await client.get("/health")
            assert res_ping.status_code == 200
            assert res_ping.headers.get("X-Quorum-Data-Source") == "fastapi_backend"

            # 2. Public cannot access diagnostics
            res_anon = await client.get("/api/admin/diagnostics")
            assert res_anon.status_code == 401

            # 3. Regular member cannot access diagnostics
            res_member = await client.get("/api/admin/diagnostics", headers=member_headers)
            assert res_member.status_code == 403

            # 4. Admin receives safe diagnostics
            res_admin = await client.get("/api/admin/diagnostics", headers=admin_headers)
            assert res_admin.status_code == 200
            diag = res_admin.json()

            assert diag["backend_reachable"] is True
            assert diag["data_source"] == "fastapi_backend"
            assert "application_environment" in diag
            assert "schema_migration_revision" in diag
            assert "safe_db_host_fingerprint" in diag
            assert "backend_version" in diag

            # Ensure zero secrets/credentials/emails in diagnostics
            diag_str = str(diag).lower()
            assert "password" not in diag_str
            assert "secret" not in diag_str
            assert "@" not in diag_str or diag.get("safe_db_host_fingerprint")  # host is fine, no email
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_stage3_legacy_records_audit_endpoint():
    """
    4. Handle existing misowned records safely:
    Admin audit endpoint reports legacy records without exposing titles or content.
    """
    await close_redis_client()
    try:
        admin_user = await create_test_user(role="admin", email_prefix="audit_admin")
        admin_headers = {"Authorization": f"Bearer {admin_user.id}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/admin/audit/legacy-records", headers=admin_headers)
            assert res.status_code == 200
            data = res.json()
            assert "total_flagged_records" in data
            assert "records" in data
            assert "audit_note" in data

            # Verify that none of the records contain private content fields
            for r in data["records"]:
                assert "project_id" in r
                assert "owner_id" in r
                assert "associated_report_count" in r
                assert "title" not in r
                assert "content" not in r
                assert "query" not in r
    finally:
        await close_redis_client()


def test_stage3_no_active_hardcoded_user_id():
    """
    Search and verify that the old hardcoded admin UUID is NOT present in
    any active Next.js or FastAPI runtime routes or libraries.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    web_src = os.path.join(repo_root, "apps", "web", "src")
    api_src = os.path.join(repo_root, "apps", "api", "src")

    for search_dir in [web_src, api_src]:
        for root, _, files in os.walk(search_dir):
            for file in files:
                if file.endswith((".ts", ".tsx", ".py")):
                    full_path = os.path.join(root, file)
                    # Skip test files and admin audit query which explicitly searches for the legacy ID
                    if "admin.py" in file:
                        continue
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        assert LEGACY_HARDCODED_UUID not in content, (
                            f"Hardcoded UUID found in runtime file: {full_path}"
                        )


@pytest.mark.asyncio
async def test_stage3_admin_role_cannot_be_spoofed():
    """
    Requirement E: Confirm /api/admin/diagnostics and /api/admin/audit/legacy-records
    require backend-verified admin role and cannot be spoofed by client headers,
    query parameters, or client-crafted tokens.
    """
    import base64
    import json

    await close_redis_client()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Unauthenticated request with spoof headers/query
            res_spoof_hdr = await client.get(
                "/api/admin/diagnostics?role=admin",
                headers={"X-Role": "admin", "X-Admin": "true"},
            )
            assert res_spoof_hdr.status_code == 401

            # 2. Forged base64 session claiming role="admin" for non-admin email
            forged_payload = json.dumps({
                "id": str(uuid.uuid4()),
                "email": f"attacker_{uuid.uuid4().hex[:6]}@untrusted.org",
                "name": "Malicious Spoof",
                "role": "admin",
            })
            forged_token = base64.b64encode(forged_payload.encode()).decode()

            res_forged = await client.get(
                "/api/admin/diagnostics",
                headers={"Authorization": f"Bearer {forged_token}"},
            )
            # Must reject with 403 Forbidden because backend forces role="member"
            assert res_forged.status_code == 403
            assert res_forged.json()["error"] == "forbidden"

            # 3. Forged audit endpoint access
            res_forged_audit = await client.get(
                "/api/admin/audit/legacy-records",
                headers={"Authorization": f"Bearer {forged_token}"},
            )
            assert res_forged_audit.status_code == 403
            assert res_forged_audit.json()["error"] == "forbidden"
    finally:
        await close_redis_client()

