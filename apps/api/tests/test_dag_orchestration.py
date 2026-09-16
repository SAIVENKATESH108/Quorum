import asyncio
import time
import uuid
import pytest
from typing import Dict, List, Set

from src.agents.base import AgentResult, TaskNode
from src.agents.engine import OrchestrationEngine, StatusPublisher, StatusEvent
from src.agents.orchestrator import OrchestratorAgent
from src.agents.providers import AIProvider
from src.db.models import AgentRole, AgentTask


class StubProvider(AIProvider):
    """Stub provider returning fast static responses."""
    name = "Stub"

    async def _call_api(self, prompt: str, system: str | None = None) -> str:
        return '{"subtopics": [{"title": "Subtopic A"}, {"title": "Subtopic B"}, {"title": "Subtopic C"}]}'


@pytest.mark.asyncio
async def test_orchestrator_generates_valid_dag():
    """Verify OrchestratorAgent generates 3-6 independent research nodes + fact_check + writer stages."""
    provider = StubProvider()
    orchestrator = OrchestratorAgent(provider)

    task = AgentTask(
        id=uuid.uuid4(),
        agent_run_id=uuid.uuid4(),
        task_type="decompose_query",
        payload={"query": "Autonomous Agent Swarms in Supply Chains"},
    )
    result = await orchestrator.run(task)

    assert result.success is True
    dag_raw = result.output["dag"]
    nodes = [TaskNode.from_dict(d) for d in dag_raw]

    # Verify at least 3 research nodes
    research_nodes = [n for n in nodes if n.agent_role == AgentRole.RESEARCHER]
    assert 3 <= len(research_nodes) <= 6

    # Research nodes must have no unmet dependencies (parallel start)
    for rn in research_nodes:
        assert len(rn.depends_on) == 0

    # Fact checker node depends on all research nodes
    fact_nodes = [n for n in nodes if n.agent_role == AgentRole.FACT_CHECKER]
    assert len(fact_nodes) == 1
    research_ids = {n.id for n in research_nodes}
    assert set(fact_nodes[0].depends_on) == research_ids

    # Writer node depends on fact checker
    writer_nodes = [n for n in nodes if n.agent_role == AgentRole.WRITER]
    assert len(writer_nodes) == 1
    assert writer_nodes[0].depends_on == [fact_nodes[0].id]


@pytest.mark.asyncio
async def test_dag_parallel_and_topological_execution():
    """
    Confirm:
    1. Independent nodes run concurrently in parallel via asyncio.gather.
    2. Dependent nodes wait until all dependencies reach succeeded status.
    """
    execution_timeline: List[tuple[str, str, float]] = []  # (event, node_id, timestamp)
    active_concurrent_nodes: Set[str] = set()
    max_observed_concurrency = 0

    nodes = [
        TaskNode(id="research_1", description="R1", task_type="r", agent_role=AgentRole.RESEARCHER, depends_on=[]),
        TaskNode(id="research_2", description="R2", task_type="r", agent_role=AgentRole.RESEARCHER, depends_on=[]),
        TaskNode(id="research_3", description="R3", task_type="r", agent_role=AgentRole.RESEARCHER, depends_on=[]),
        TaskNode(
            id="fact_check",
            description="FC",
            task_type="fc",
            agent_role=AgentRole.FACT_CHECKER,
            depends_on=["research_1", "research_2", "research_3"],
        ),
        TaskNode(
            id="writer",
            description="W",
            task_type="w",
            agent_role=AgentRole.WRITER,
            depends_on=["fact_check"],
        ),
    ]

    completed_nodes: Set[str] = set()

    async def mock_execute_node(node: TaskNode) -> AgentResult:
        nonlocal max_observed_concurrency
        # Verify all dependencies are already in completed_nodes
        for dep in node.depends_on:
            assert dep in completed_nodes, f"Dependency '{dep}' not satisfied for node '{node.id}'"

        active_concurrent_nodes.add(node.id)
        max_observed_concurrency = max(max_observed_concurrency, len(active_concurrent_nodes))
        t_start = time.monotonic()
        execution_timeline.append(("start", node.id, t_start))

        # Simulate async work (50ms)
        await asyncio.sleep(0.05)

        t_end = time.monotonic()
        execution_timeline.append(("end", node.id, t_end))
        active_concurrent_nodes.remove(node.id)
        completed_nodes.add(node.id)

        return AgentResult(success=True, output={"node_id": node.id})

    # Simulate engine DAG resolution loop
    while len(completed_nodes) < len(nodes):
        ready = [
            n for n in nodes
            if n.id not in completed_nodes and all(d in completed_nodes for d in n.depends_on)
        ]
        assert len(ready) > 0, "Deadlock in DAG"

        # Concurrently execute all ready nodes
        await asyncio.gather(*[mock_execute_node(n) for n in ready])

    # 1. Verify concurrency: research_1, research_2, research_3 ran together
    assert max_observed_concurrency == 3, f"Expected concurrency of 3, got {max_observed_concurrency}"

    # 2. Verify topological order:
    # All research end times must be <= fact_check start time
    research_ends = [t for (evt, nid, t) in execution_timeline if evt == "end" and nid.startswith("research_")]
    fact_check_starts = [t for (evt, nid, t) in execution_timeline if evt == "start" and nid == "fact_check"]
    writer_starts = [t for (evt, nid, t) in execution_timeline if evt == "start" and nid == "writer"]
    fact_check_ends = [t for (evt, nid, t) in execution_timeline if evt == "end" and nid == "fact_check"]

    assert max(research_ends) <= fact_check_starts[0]
    assert fact_check_ends[0] <= writer_starts[0]


@pytest.mark.asyncio
async def test_status_publisher_events():
    """Verify StatusPublisher broadcasts events correctly to registered callbacks."""
    publisher = StatusPublisher()
    received_events: List[StatusEvent] = []

    async def listener(event: StatusEvent):
        received_events.append(event)

    publisher.subscribe(listener)

    report_id = uuid.uuid4()
    await publisher.publish(
        StatusEvent(
            event_type="test_event",
            report_id=report_id,
            status="researching",
            agent_role="researcher",
        )
    )

    assert len(received_events) == 1
    assert received_events[0].event_type == "test_event"
    assert received_events[0].report_id == report_id
    assert received_events[0].status == "researching"


@pytest.mark.asyncio
async def test_orchestration_engine_executes_dag_to_completion():
    """Verify OrchestrationEngine executes full DAG, updates report status, and generates sections."""
    from src.db.session import async_session_maker
    from src.db.models import User, Project, Report, ReportStatus, ReportSection
    from sqlalchemy import select

    provider = StubProvider()
    published_events: List[StatusEvent] = []

    publisher = StatusPublisher()
    async def event_collector(e):
        published_events.append(e)
    publisher.subscribe(event_collector)

    engine = OrchestrationEngine(provider=provider, session_factory=async_session_maker, publisher=publisher)

    # Create temporary report in DB
    report_id = uuid.uuid4()
    async with async_session_maker() as session:
        user = User(id=uuid.uuid4(), email=f"test_{report_id.hex[:6]}@quorum.ai", name="Test User")
        project = Project(id=uuid.uuid4(), user_id=user.id, title="Test DAG Project")
        report = Report(id=report_id, project_id=project.id, query="Future of Autonomous AI Swarms", status=ReportStatus.PENDING)
        session.add(user)
        session.add(project)
        session.add(report)
        await session.commit()

    # Run full report pipeline
    success = await engine.run_report(report_id)
    assert success is True

    # Verify report status is COMPLETE in DB
    async with async_session_maker() as session:
        stmt = select(Report).where(Report.id == report_id)
        res = await session.execute(stmt)
        updated_report = res.scalars().first()
        assert updated_report is not None
        assert updated_report.status == ReportStatus.COMPLETE
        assert updated_report.completed_at is not None

        # Verify sections created
        stmt_sec = select(ReportSection).where(ReportSection.report_id == report_id)
        res_sec = await session.execute(stmt_sec)
        sections = res_sec.scalars().all()
        assert len(sections) >= 3

    # Verify events were published for planning, researching, and completion
    event_types = [e.event_type for e in published_events]
    assert "report_status_changed" in event_types
    assert "task_started" in event_types
    assert "task_completed" in event_types

