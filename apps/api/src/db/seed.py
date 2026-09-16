import asyncio
import sys
import uuid
from sqlalchemy import select
from src.db.session import async_session_maker
from src.db.models import User, Project, Report, ReportStatus


async def seed_data() -> None:
    """Seed initial testing data into the database."""
    print("[SEED] Starting database seeding...")

    async with async_session_maker() as session:
        # 1. Check or create test user
        user_email = "test@quorum.ai"
        stmt = select(User).where(User.email == user_email)
        result = await session.execute(stmt)
        user = result.scalars().first()

        if not user:
            user = User(
                id=uuid.uuid4(),
                email=user_email,
                name="Quorum Test User",
            )
            session.add(user)
            await session.flush()
            print(f"[SEED] Created test user: {user.email} (id: {user.id})")
        else:
            print(f"[SEED] Test user already exists: {user.email} (id: {user.id})")

        # 2. Check or create test project
        stmt = select(Project).where(
            Project.user_id == user.id,
            Project.title == "AI Multi-Agent Research Platform",
        )
        result = await session.execute(stmt)
        project = result.scalars().first()

        if not project:
            project = Project(
                id=uuid.uuid4(),
                user_id=user.id,
                title="AI Multi-Agent Research Platform",
            )
            session.add(project)
            await session.flush()
            print(f"[SEED] Created test project: '{project.title}' (id: {project.id})")
        else:
            print(f"[SEED] Test project already exists: '{project.title}' (id: {project.id})")

        # 3. Check or create test report in "pending" status
        stmt = select(Report).where(
            Report.project_id == project.id,
            Report.query == "Deep Dive: Autonomous Multi-Agent Consensus Mechanisms",
        )
        result = await session.execute(stmt)
        report = result.scalars().first()

        if not report:
            report = Report(
                id=uuid.uuid4(),
                project_id=project.id,
                status=ReportStatus.PENDING,
                query="Deep Dive: Autonomous Multi-Agent Consensus Mechanisms",
            )
            session.add(report)
            await session.flush()
            print(f"[SEED] Created test report: status='{report.status.value}' (id: {report.id})")
        else:
            print(f"[SEED] Test report already exists: status='{report.status.value}' (id: {report.id})")

        await session.commit()
        print("[SEED] Database seeding completed successfully!")


def main() -> None:
    """CLI entrypoint for seed script."""
    try:
        asyncio.run(seed_data())
    except Exception as e:
        print(f"[ERROR] Database seeding failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
