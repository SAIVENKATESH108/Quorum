import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from arq.connections import RedisSettings
from sqlalchemy import select, update

from src.agents.base import AgentResult
from src.agents.commands import AgentTaskCommand
from src.agents.factory import AgentFactory
from src.agents.providers import ProviderFallbackChain
from src.core.config import settings
from src.core.events import format_report_channel, publish_event
from src.db.models import (
    AgentRole,
    AgentRun,
    AgentRunStatus,
    AgentTask,
    AgentTaskStatus,
    ReportSection,
    ReportSource,
    Source,
)
from src.db.session import async_session_maker

logger = logging.getLogger(__name__)


# Default provider fallback chain for worker jobs
# Uses OpenRouter (free tier) → Gemini → OpenAI
def get_default_provider() -> ProviderFallbackChain:
    from src.agents.providers import get_default_provider as _get
    return _get()


async def process_agent_task(ctx: Optional[Dict[str, Any]], command_data: Dict[str, Any], provider: Optional[Any] = None) -> Dict[str, Any]:
    """
    Job queue task processing an AgentTaskCommand:
    1. Deserializes the AgentTaskCommand
    2. Retrieves context and associated report & agent run from database
    3. Updates agent_tasks and agent_runs to RUNNING
    4. Publishes real-time status event to Redis channel: report:{report_id}:events
    5. Executes command via the concrete Agent
    6. Updates database rows (agent_tasks, agent_runs, report_sections, sources) with outcomes
    7. Publishes final completion/failure event
    """
    command = AgentTaskCommand.from_dict(command_data)
    run_id = command.agent_run_id

    async with async_session_maker() as session:
        # Fetch AgentRun to find report_id and agent_role
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        res = await session.execute(stmt)
        agent_run = res.scalars().first()
        if not agent_run:
            raise ValueError(f"AgentRun {run_id} not found in database.")

        report_id = agent_run.report_id
        agent_role = agent_run.agent_role

        # Fetch or verify AgentTask
        task_stmt = select(AgentTask).where(AgentTask.agent_run_id == run_id)
        task_res = await session.execute(task_stmt)
        agent_task = task_res.scalars().first()
        if not agent_task:
            agent_task = AgentTask(
                id=uuid.uuid4(),
                agent_run_id=run_id,
                task_type=command.task_type,
                status=AgentTaskStatus.RUNNING,
                payload=command.payload,
                retry_count=command.retry_count,
            )
            session.add(agent_task)
        else:
            agent_task.status = AgentTaskStatus.RUNNING
            agent_task.retry_count = command.retry_count

        agent_run.status = AgentRunStatus.RUNNING
        agent_run.started_at = datetime.now(timezone.utc)
        await session.commit()
        task_id = agent_task.id

    channel = format_report_channel(report_id)

    # Publish task started event
    await publish_event(
        channel,
        {
            "type": "task_status",
            "data": {
                "report_id": str(report_id),
                "run_id": str(run_id),
                "task_id": str(task_id),
                "agent_role": agent_role.value,
                "task_type": command.task_type,
                "status": "running",
                "attempt": command.retry_count + 1,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Instantiate Agent and execute command
    if provider is None:
        provider = get_default_provider()
    agent = AgentFactory.create(agent_role, provider)

    result: AgentResult
    try:
        result = await command.execute(agent, agent_task)
    except Exception as exc:
        logger.error(f"[WORKER] Unexpected error in agent execution: {exc}")
        result = AgentResult(success=False, error=str(exc))

    final_run_status = AgentRunStatus.SUCCEEDED if result.success else AgentRunStatus.FAILED
    final_task_status = AgentTaskStatus.SUCCEEDED if result.success else AgentTaskStatus.FAILED

    async with async_session_maker() as session:
        await session.execute(
            update(AgentRun)
            .where(AgentRun.id == run_id)
            .values(
                status=final_run_status,
                completed_at=datetime.now(timezone.utc),
                error_message=result.error if not result.success else None,
            )
        )
        await session.execute(
            update(AgentTask)
            .where(AgentTask.id == task_id)
            .values(
                status=final_task_status,
                retry_count=command.retry_count,
                result=result.output if result.success else None,
            )
        )

        # Persist sources if researcher generated claims
        if result.success and agent_role == AgentRole.RESEARCHER:
            claims = result.output.get("claims", [])
            for claim in claims:
                url = claim.get("source_url")
                if not url:
                    continue
                title = claim.get("source_title") or f"Scholarly Reference: {claim.get('claim_text', '')[:70]}"

                src_stmt = select(Source).where(Source.url == url)
                src_res = await session.execute(src_stmt)
                source_rec = src_res.scalars().first()
                if not source_rec:
                    source_rec = Source(
                        id=uuid.uuid4(),
                        url=url[:2048],
                        title=title[:512],
                    )
                    session.add(source_rec)
                    await session.flush()

                rs_stmt = select(ReportSource).where(
                    ReportSource.report_id == report_id,
                    ReportSource.source_id == source_rec.id,
                )
                rs_res = await session.execute(rs_stmt)
                if not rs_res.scalars().first():
                    session.add(ReportSource(report_id=report_id, source_id=source_rec.id))

        # Persist codebase module sources if document analyzer generated codebase_claims
        if result.success and agent_role == AgentRole.DOCUMENT_ANALYZER:
            for claim in result.output.get("codebase_claims", []):
                file_path = claim.get("file_path")
                if not file_path:
                    continue
                blob_url = claim.get("blob_url") or f"file:///{file_path}"
                title = f"Codebase Module: {file_path}"

                src_stmt = select(Source).where(Source.url == blob_url)
                src_res = await session.execute(src_stmt)
                source_rec = src_res.scalars().first()
                if not source_rec:
                    source_rec = Source(
                        id=uuid.uuid4(),
                        url=blob_url[:2048],
                        title=title[:512],
                    )
                    session.add(source_rec)
                    await session.flush()

                rs_stmt = select(ReportSource).where(
                    ReportSource.report_id == report_id,
                    ReportSource.source_id == source_rec.id,
                )
                rs_res = await session.execute(rs_stmt)
                if not rs_res.scalars().first():
                    session.add(ReportSource(report_id=report_id, source_id=source_rec.id))

        # If WriterAgent successfully generated sections, persist them
        if result.success and agent_role == AgentRole.WRITER:
            sections = result.output.get("sections", [])
            for sec in sections:
                heading = str(sec.get("heading", "Section"))[:250]
                section_model = ReportSection(
                    id=uuid.uuid4(),
                    report_id=report_id,
                    heading=heading,
                    content=sec.get("content", ""),
                    order_index=sec.get("order_index", 1),
                )
                session.add(section_model)
                await session.flush()

                for cite_url in sec.get("citations", []):
                    if not cite_url:
                        continue
                    src_stmt = select(Source).where(Source.url == cite_url)
                    src_res = await session.execute(src_stmt)
                    source_rec = src_res.scalars().first()
                    if not source_rec:
                        if "github.com" in cite_url or "file:///" in cite_url:
                            file_part = cite_url.split("/")[-1].split("#")[0]
                            title = f"Source Module: {file_part}"
                        else:
                            title = f"Cited Reference: {heading[:80]}"

                        source_rec = Source(
                            id=uuid.uuid4(),
                            url=cite_url[:2048],
                            title=title[:512],
                        )
                        session.add(source_rec)
                        await session.flush()

                    rs_stmt = select(ReportSource).where(
                        ReportSource.report_id == report_id,
                        ReportSource.source_id == source_rec.id,
                    )
                    rs_res = await session.execute(rs_stmt)
                    if not rs_res.scalars().first():
                        session.add(
                            ReportSource(
                                report_id=report_id,
                                source_id=source_rec.id,
                                cited_in_section_id=section_model.id,
                            )
                        )

        await session.commit()

    # Publish final event
    await publish_event(
        channel,
        {
            "type": "task_status",
            "data": {
                "report_id": str(report_id),
                "run_id": str(run_id),
                "task_id": str(task_id),
                "agent_role": agent_role.value,
                "task_type": command.task_type,
                "status": "succeeded" if result.success else "failed",
                "result": result.output if result.success else None,
                "error": result.error,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    if not result.success and command.is_retryable(result.error):
        command.increment_retry()
        # Raise RuntimeError so arq queue / engine can re-enqueue or track retry
        raise RuntimeError(f"Task failed (retryable): {result.error}")

    return result.to_dict()


class WorkerSettings:
    """arq Worker settings configuration."""

    functions = [process_agent_task]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL or "redis://localhost:6379/0")
    max_jobs = 10
    job_timeout = 300
    max_retries = 3


if __name__ == "__main__":
    import sys
    from arq import run_worker
    try:
        print(f"[WORKER] Starting Arq agent worker with Redis: {settings.REDIS_URL}...")
        run_worker(WorkerSettings)
    except (TimeoutError, Exception):
        print(f"\n[WORKER INFO] Could not connect to Redis at '{settings.REDIS_URL}'.")
        print("To run the dedicated worker locally, start Redis using Docker:")
        print("  docker run -d -p 6379:6379 redis:7-alpine")
        print("\nNote: For local development, the FastAPI backend already processes agent workflows")
        print("automatically in in-process background tasks! You do NOT need this worker running.")
        sys.exit(0)

