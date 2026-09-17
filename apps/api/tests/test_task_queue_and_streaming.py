import asyncio
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from src.agents.commands import AgentTaskCommand
from src.core.events import format_report_channel, publish_event, subscribe_to_channel
from src.core.redis import close_redis_client
from src.db.models import (
    AgentRole,
    AgentRun,
    AgentRunStatus,
    AgentTask,
    AgentTaskStatus,
    Project,
    Report,
    ReportStatus,
    User,
)
from src.db.session import async_session_maker
from src.workers.main import process_agent_task
from src.agents.providers import AIProvider


class StubProvider(AIProvider):
    name = "Stub"
    async def _call_api(self, prompt: str, system: str | None = None) -> str:
        return '{"subtopics": [{"title": "Subtopic A"}], "claims": [{"claim_text": "Sample claim", "source_url": "https://example.com"}]}'


async def create_test_report_hierarchy() -> tuple[User, Project, Report]:
    """Helper creating a test user, project, and report in the database."""
    async with async_session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"tester_{uuid.uuid4().hex[:8]}@quorum.ai",
            name="Queue Integration Tester",
        )
        project = Project(
            id=uuid.uuid4(),
            user_id=user.id,
            title="Distributed Systems Benchmark",
        )
        report = Report(
            id=uuid.uuid4(),
            project_id=project.id,
            query="Fault-Tolerant Consensus in Asynchronous Networks",
            status=ReportStatus.PENDING,
        )
        session.add(user)
        session.add(project)
        session.add(report)
        await session.commit()
        return user, project, report


@pytest.mark.asyncio
async def test_worker_processes_task_and_publishes_event():
    """
    Integration test:
    1. Creates a report via helper function
    2. Subscribes to the report's Redis pub/sub channel
    3. Enqueues and executes a task
    4. Asserts DB row updated to 'succeeded'
    5. Asserts event was published to the correct Redis channel
    """
    await close_redis_client()
    try:
        user, project, report = await create_test_report_hierarchy()
        report_id = report.id
        channel = format_report_channel(report_id)

        # 1. Create an AgentRun row in DB
        run_id = uuid.uuid4()
        async with async_session_maker() as session:
            agent_run = AgentRun(
                id=run_id,
                report_id=report_id,
                agent_role=AgentRole.RESEARCHER,
                status=AgentRunStatus.QUEUED,
            )
            session.add(agent_run)
            await session.commit()

        # 2. Listen to Redis channel in background
        received_events = []
        stop_listener = asyncio.Event()

        async def channel_listener():
            async for event in subscribe_to_channel(channel):
                received_events.append(event)
                if event.get("data", {}).get("status") == "succeeded":
                    stop_listener.set()
                if stop_listener.is_set():
                    break

        listener_task = asyncio.create_task(channel_listener())
        await asyncio.sleep(0.1)  # Allow subscription to establish

        # 3. Create command and process via worker
        command = AgentTaskCommand(
            agent_run_id=run_id,
            task_type="research_subtopic",
            payload={
                "query": report.query,
                "title": "Byzantine Fault Tolerance in Asynchronous Networks",
                "description": "Evaluate liveness and safety bounds.",
            },
        )

        result = await process_agent_task(ctx=None, command_data=command.to_dict(), provider=StubProvider())
        assert result.get("success") is True

        # 4. Wait for event listener to capture events
        try:
            await asyncio.wait_for(stop_listener.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pass
        finally:
            listener_task.cancel()

        # 5. Assert DB rows updated to 'succeeded'
        async with async_session_maker() as session:
            # Check AgentRun
            stmt_run = select(AgentRun).where(AgentRun.id == run_id)
            res_run = await session.execute(stmt_run)
            updated_run = res_run.scalars().first()
            assert updated_run is not None
            assert updated_run.status == AgentRunStatus.SUCCEEDED
            assert updated_run.completed_at is not None

            # Check AgentTask
            stmt_task = select(AgentTask).where(AgentTask.agent_run_id == run_id)
            res_task = await session.execute(stmt_task)
            updated_task = res_task.scalars().first()
            assert updated_task is not None
            assert updated_task.status == AgentTaskStatus.SUCCEEDED
            assert updated_task.result is not None
            assert "claims" in updated_task.result

        # 6. Assert events were published to the correct Redis channel
        assert len(received_events) >= 1
        event_statuses = [e.get("data", {}).get("status") for e in received_events]
        assert "succeeded" in event_statuses
        assert any(e.get("type") == "task_status" for e in received_events)
    finally:
        await close_redis_client()


@pytest.mark.asyncio
async def test_websocket_endpoint_authorization_and_streaming():
    """
    Test WebSocket /ws/reports/{report_id}:
    - Unowned/unauthorized report returns 1008 policy violation
    - Owned report connects and receives forwarded Redis pub/sub events
    """
    await close_redis_client()
    try:
        from src.api.websocket import stream_report_status

        user, project, report = await create_test_report_hierarchy()
        other_user, _, _ = await create_test_report_hierarchy()

        class MockWebSocket:
            def __init__(self):
                self.accepted = False
                self.closed = False
                self.close_code = None
                self.sent_messages = []

            async def accept(self):
                self.accepted = True

            async def send_json(self, data):
                self.sent_messages.append(data)
                # Raise WebSocketDisconnect after first message to exit stream loop cleanly
                from fastapi import WebSocketDisconnect
                raise WebSocketDisconnect()

            async def close(self, code=1000, reason=None):
                self.closed = True
                self.close_code = code

        # 1. Test unauthorized user trying to stream report
        unauth_ws = MockWebSocket()
        await stream_report_status(websocket=unauth_ws, report_id=report.id, current_user=other_user)
        assert unauth_ws.closed is True
        assert unauth_ws.close_code == 1008
        assert unauth_ws.accepted is False

        # 2. Test authorized owner connecting and receiving streamed events
        auth_ws = MockWebSocket()
        channel = format_report_channel(report.id)

        async def send_periodic_events():
            # Publish periodically so that message is received once websocket subscription is active
            await asyncio.sleep(0.5)
            for _ in range(60):
                if auth_ws.sent_messages:
                    break
                await publish_event(
                    channel,
                    {
                        "type": "report_status",
                        "data": {"status": "researching", "progress": 50},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                await asyncio.sleep(0.25)

        event_task = asyncio.create_task(send_periodic_events())
        try:
            await stream_report_status(websocket=auth_ws, report_id=report.id, current_user=user)
        finally:
            event_task.cancel()

        assert auth_ws.accepted is True
        assert len(auth_ws.sent_messages) >= 1
        msg = auth_ws.sent_messages[0]
        assert msg["type"] == "report_status"
        assert msg["data"]["status"] == "researching"
        assert msg["data"]["progress"] == 50
        assert "timestamp" in msg
    finally:
        await close_redis_client()
