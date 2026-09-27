import os
import uuid
import datetime
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import jwt
from src.core.config import settings
from src.core.redis import close_redis_client
from src.db.models import Project, Report, ReportSource, ReportStatus, Source, User, UserRole
from src.db.session import async_session_maker
from src.main import app


async def create_user(role: str = "member", email_prefix: str = "test") -> User:
    async with async_session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"{email_prefix}_{uuid.uuid4().hex[:8]}@quorum.ai",
            name=f"User {role}",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def make_token(user: User) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(hours=2)).timestamp()),
    }
    secret = settings.AUTH_SECRET_KEY or "local-only-change-this-auth-secret"
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_stage5_unauthenticated_requests_receive_401():
    """
    Unauthenticated requests to:
    - GET /api/sources
    - GET /api/sources/stats
    - GET /api/reports/counts
    must receive HTTP 401 Unauthorized.
    """
    await close_redis_client()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res_s = await client.get("/api/sources")
            assert res_s.status_code == 401

            res_stats = await client.get("/api/sources/stats")
            assert res_stats.status_code == 401

            res_counts = await client.get("/api/reports/counts")
            assert res_counts.status_code == 401
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_stage5_source_stats_and_category_filter():
    """
    Tests:
    1. GET /api/sources and GET /api/sources/stats share identical category filtering and scope.
    2. Category filtering scopes both list and stats.
    3. Academic domain count accurately uses URL heuristic.
    4. Explanatory note is present.
    """
    await close_redis_client()
    try:
        user = await create_user(role="member", email_prefix="src_owner")
        token = make_token(user)
        headers = {"Authorization": f"Bearer {token}"}

        async with async_session_maker() as session:
            p = Project(id=uuid.uuid4(), user_id=user.id, title="Sources Project", is_guest_demo=False)
            session.add(p)
            await session.flush()

            r = Report(
                id=uuid.uuid4(),
                project_id=p.id,
                query="Quantum Neural Physics",
                status=ReportStatus.COMPLETE.value,
                is_guest_demo=False,
            )
            session.add(r)
            await session.flush()

            # Create 3 sources: 1 academic (arxiv), 1 technical (github), 1 general
            s_acad = Source(
                id=uuid.uuid4(),
                url="https://arxiv.org/abs/2603.12345",
                title="Quantum Computing Scaling",
            )
            s_tech = Source(
                id=uuid.uuid4(),
                url="https://github.com/torvalds/linux",
                title="Linux Kernel",
            )
            s_gen = Source(
                id=uuid.uuid4(),
                url="https://example.com/blog/ai",
                title="Example AI Post",
            )
            session.add_all([s_acad, s_tech, s_gen])
            await session.flush()

            rs1 = ReportSource(report_id=r.id, source_id=s_acad.id)
            rs2 = ReportSource(report_id=r.id, source_id=s_tech.id)
            rs3 = ReportSource(report_id=r.id, source_id=s_gen.id)
            session.add_all([rs1, rs2, rs3])
            await session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Unfiltered
            res_all = await client.get("/api/sources", headers=headers)
            assert res_all.status_code == 200
            items = res_all.json()
            assert len(items) == 3

            res_stats = await client.get("/api/sources/stats", headers=headers)
            assert res_stats.status_code == 200
            stats = res_stats.json()
            assert stats["total"] == 3
            assert stats["academic_domain_count"] == 1
            assert stats["filtered_by_category"] is None
            assert "heuristic" in stats["note"].lower() or "not a verified" in stats["note"].lower()

            # 2. Filter by academic
            res_acad = await client.get("/api/sources?category=academic", headers=headers)
            assert res_acad.status_code == 200
            acad_items = res_acad.json()
            assert len(acad_items) == 1
            assert acad_items[0]["domain"] == "arxiv.org"
            assert acad_items[0]["category"] == "academic"

            res_acad_stats = await client.get("/api/sources/stats?category=academic", headers=headers)
            assert res_acad_stats.status_code == 200
            acad_stats = res_acad_stats.json()
            assert acad_stats["total"] == 1
            assert acad_stats["academic_domain_count"] == 1
            assert acad_stats["filtered_by_category"] == "academic"

            # 3. Filter by technical
            res_tech_stats = await client.get("/api/sources/stats?category=technical", headers=headers)
            assert res_tech_stats.status_code == 200
            tech_stats = res_tech_stats.json()
            assert tech_stats["total"] == 1
            assert tech_stats["academic_domain_count"] == 0
            assert tech_stats["filtered_by_category"] == "technical"
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_stage5_linked_report_count_distinct_reports():
    """
    Verify linked_report_count counts DISTINCT visible reports,
    not reference/citation occurrences.
    """
    await close_redis_client()
    try:
        user = await create_user(role="member", email_prefix="src_linked")
        token = make_token(user)
        headers = {"Authorization": f"Bearer {token}"}

        async with async_session_maker() as session:
            p = Project(id=uuid.uuid4(), user_id=user.id, title="Multi Report Project", is_guest_demo=False)
            session.add(p)
            await session.flush()

            r1 = Report(id=uuid.uuid4(), project_id=p.id, query="Report 1", status=ReportStatus.COMPLETE.value)
            r2 = Report(id=uuid.uuid4(), project_id=p.id, query="Report 2", status=ReportStatus.COMPLETE.value)
            session.add_all([r1, r2])
            await session.flush()

            # Source shared across 2 reports
            shared_source = Source(
                id=uuid.uuid4(),
                url="https://nature.com/articles/quantum-breakthrough",
                title="Quantum Breakthrough",
            )
            session.add(shared_source)
            await session.flush()

            rs1 = ReportSource(report_id=r1.id, source_id=shared_source.id)
            rs2 = ReportSource(report_id=r2.id, source_id=shared_source.id)
            session.add_all([rs1, rs2])
            await session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/sources", headers=headers)
            assert res.status_code == 200
            items = res.json()
            matching = [item for item in items if item["id"] == str(shared_source.id)]
            assert len(matching) == 1
            assert matching[0]["linked_report_count"] == 2
            assert matching[0]["occurrence_count"] == 2
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_stage5_reports_pagination_and_status_filtering():
    """
    Verify reports pagination envelope (items, total, limit, offset, has_more),
    status filtering (in_progress maps to researching, fact_checking, writing),
    and counts endpoint.
    """
    await close_redis_client()
    try:
        user = await create_user(role="member", email_prefix="rep_filter")
        token = make_token(user)
        headers = {"Authorization": f"Bearer {token}"}

        async with async_session_maker() as session:
            p = Project(id=uuid.uuid4(), user_id=user.id, title="Pagination Project", is_guest_demo=False)
            session.add(p)
            await session.flush()

            # Create reports in diverse statuses
            r_pend = Report(id=uuid.uuid4(), project_id=p.id, query="Report Pending", status=ReportStatus.PENDING.value)
            r_plan = Report(id=uuid.uuid4(), project_id=p.id, query="Report Planning", status=ReportStatus.PLANNING.value)
            r_res = Report(id=uuid.uuid4(), project_id=p.id, query="Report Researching", status=ReportStatus.RESEARCHING.value)
            r_fact = Report(id=uuid.uuid4(), project_id=p.id, query="Report Fact Checking", status=ReportStatus.FACT_CHECKING.value)
            r_wri = Report(id=uuid.uuid4(), project_id=p.id, query="Report Writing", status=ReportStatus.WRITING.value)
            r_comp = Report(id=uuid.uuid4(), project_id=p.id, query="Report Complete", status=ReportStatus.COMPLETE.value)
            r_rev = Report(id=uuid.uuid4(), project_id=p.id, query="Report Needs Review", status=ReportStatus.NEEDS_REVIEW.value)
            r_fail = Report(id=uuid.uuid4(), project_id=p.id, query="Report Failed", status=ReportStatus.FAILED.value)

            session.add_all([r_pend, r_plan, r_res, r_fact, r_wri, r_comp, r_rev, r_fail])
            await session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Check /api/reports/counts
            res_c = await client.get("/api/reports/counts", headers=headers)
            assert res_c.status_code == 200
            counts = res_c.json()
            assert counts["all"] == 8
            assert counts["pending"] == 1
            assert counts["planning"] == 1
            # in_progress must be researching(1) + fact_checking(1) + writing(1) = 3
            assert counts["in_progress"] == 3
            assert counts["complete"] == 1
            assert counts["needs_review"] == 1
            assert counts["failed"] == 1

            # 2. Check /api/reports?status=in_progress
            res_prog = await client.get("/api/reports?status=in_progress", headers=headers)
            assert res_prog.status_code == 200
            data_prog = res_prog.json()
            assert data_prog["total"] == 3
            assert len(data_prog["items"]) == 3
            for item in data_prog["items"]:
                assert item["status"] in ["researching", "fact_checking", "writing"]

            # 3. Check pagination with limit=2, offset=0
            res_p1 = await client.get("/api/reports?limit=2&offset=0", headers=headers)
            assert res_p1.status_code == 200
            page1 = res_p1.json()
            assert len(page1["items"]) == 2
            assert page1["total"] == 8
            assert page1["has_more"] is True
            assert page1["offset"] == 0
            assert page1["limit"] == 2

            # 4. Check pagination page 2 with limit=2, offset=2
            res_p2 = await client.get("/api/reports?limit=2&offset=2", headers=headers)
            assert res_p2.status_code == 200
            page2 = res_p2.json()
            assert len(page2["items"]) == 2
            assert page2["offset"] == 2
            # Verify distinct items between pages
            p1_ids = {r["id"] for r in page1["items"]}
            p2_ids = {r["id"] for r in page2["items"]}
            assert p1_ids.isdisjoint(p2_ids)
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_stage5_guest_isolation_sources_and_report_counts():
    """
    Verify guest sees only demo reports and demo sources.
    No private sources or report counts are leaked in GET /api/sources/stats or GET /api/reports/counts.
    """
    await close_redis_client()
    try:
        # Create private owner project & report & source
        owner = await create_user(role="member", email_prefix="private_owner")
        async with async_session_maker() as session:
            p_priv = Project(id=uuid.uuid4(), user_id=owner.id, title="Top Secret Project", is_guest_demo=False)
            session.add(p_priv)
            await session.flush()

            r_priv = Report(
                id=uuid.uuid4(),
                project_id=p_priv.id,
                query="Secret Patent Analysis",
                status=ReportStatus.COMPLETE.value,
                is_guest_demo=False,
            )
            session.add(r_priv)
            await session.flush()

            s_priv = Source(
                id=uuid.uuid4(),
                url="https://internal.company.com/confidential-patent",
                title="Confidential Patent",
            )
            session.add(s_priv)
            await session.flush()

            session.add(ReportSource(report_id=r_priv.id, source_id=s_priv.id))
            await session.commit()

        # Create guest session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res_g = await client.post("/api/auth/guest")
            assert res_g.status_code == 200
            client.cookies.update(res_g.cookies)

            # 1. Guest GET /api/sources — private source MUST NOT appear
            res_sources = await client.get("/api/sources")
            assert res_sources.status_code == 200
            guest_sources = res_sources.json()
            for s in guest_sources:
                assert s["id"] != str(s_priv.id)
                assert "internal.company.com" not in s["url"]

            # 2. Guest GET /api/sources/stats — stats MUST NOT count private sources
            res_stats = await client.get("/api/sources/stats")
            assert res_stats.status_code == 200
            guest_stats = res_stats.json()
            # If demo sources exist in DB, total will equal len(guest_sources); definitely cannot include s_priv
            assert guest_stats["total"] == len(guest_sources)

            # 3. Guest GET /api/reports/counts — counts MUST NOT count private report
            res_counts = await client.get("/api/reports/counts")
            assert res_counts.status_code == 200
            guest_counts = res_counts.json()
            # Check /api/reports for guest
            res_reports = await client.get("/api/reports")
            assert res_reports.status_code == 200
            demo_reports_total = res_reports.json()["total"]
            assert guest_counts["all"] == demo_reports_total
    finally:
        await close_redis_client()
