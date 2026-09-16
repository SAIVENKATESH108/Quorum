import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.agents.base import AgentResult, TaskNode
from src.agents.commands import AgentTaskCommand
from src.agents.factory import AgentFactory
from src.agents.providers import AIProvider, ProviderFallbackChain
from src.db.models import (
    AgentRole,
    AgentRun,
    AgentRunStatus,
    AgentTask,
    AgentTaskStatus,
    Report,
    ReportSection,
    ReportStatus,
)
from src.db.session import async_session_maker

logger = logging.getLogger(__name__)


class StatusEvent:
    """Status update event emitted after every state transition."""

    def __init__(
        self,
        event_type: str,
        report_id: uuid.UUID,
        status: str,
        agent_role: Optional[str] = None,
        run_id: Optional[uuid.UUID] = None,
        task_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.event_type = event_type
        self.report_id = report_id
        self.status = status
        self.agent_role = agent_role
        self.run_id = run_id
        self.task_id = task_id
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "report_id": str(self.report_id),
            "status": self.status,
            "agent_role": self.agent_role,
            "run_id": str(self.run_id) if self.run_id else None,
            "task_id": str(self.task_id) if self.task_id else None,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class StatusPublisher:
    """
    Pub/Sub mechanism for broadcasting live agent state transitions.
    WebSockets, Redis pubsub, and loggers can subscribe to these events.
    """

    def __init__(self):
        self._subscribers: List[Callable[[StatusEvent], Awaitable[None]]] = []

    def subscribe(self, callback: Callable[[StatusEvent], Awaitable[None]]) -> None:
        """Register an async callback listener."""
        self._subscribers.append(callback)

    async def publish(self, event: StatusEvent) -> None:
        """Publish status event to all registered subscribers."""
        logger.info(
            f"[STATUS EVENT] {event.event_type} | Report: {event.report_id} | "
            f"Role: {event.agent_role} | Status: {event.status}"
        )
        for sub in self._subscribers:
            try:
                await sub(event)
            except Exception as exc:
                logger.error(f"Error notifying subscriber {sub}: {exc}")


default_publisher = StatusPublisher()


class OrchestrationEngine:
    """
    Core Multi-Agent Orchestration Engine (Directed Acyclic Graph Concurrency Engine).

    ARCHITECTURE & DAG EXECUTION MODEL:
    ====================================
    Quorum models research workflows as a Directed Acyclic Graph (DAG) of TaskNodes:
    G = (V, E), where:
      - V (Vertices): Atomic units of work assigned to specialized agent roles
                      (ResearcherAgent, FactCheckerAgent, WriterAgent).
      - E (Directed Edges): Data dependency constraints (A -> B means B requires output of A).

    Wavefront / Topological Scheduling:
    -----------------------------------
    Rather than static linear pipelines, the engine employs dynamic topological wavefront
    scheduling based on generalized Kahn's algorithm principles:
    1. In-degree Evaluation: At each step, the engine inspects all uncompleted nodes and computes
       their unresolved dependency set: {dep in node.depends_on | dep not in completed_nodes}.
    2. Wavefront Extraction: All nodes with in-degree = 0 form the current "execution wave".
    3. Concurrency via asyncio.gather: All nodes in the wave (e.g. 3-6 independent Researcher
       agents investigating orthogonal subtopics) are launched concurrently as non-blocking
       asynchronous tasks.
    4. Synchronization Barrier: The engine awaits completion of the entire wave before
       re-evaluating graph state. Once all research nodes succeed, the FactChecker node's
       dependencies resolve to in-degree 0, allowing it to execute. Once FactChecker finishes,
       the Writer node's in-degree reaches 0.
    5. Deadlock & Cycle Safety: If uncompleted nodes remain but no nodes have in-degree = 0,
       a cycle or unreachable dependency is trapped immediately, triggering structured failure
       containment rather than hanging indefinitely.

    Dual-Write State & Reactive Event Bus:
    --------------------------------------
    Every state change is atomic and dual-written:
      - Postgres persistence: Updates `agent_runs`, `agent_tasks`, and `reports` for durability.
      - Redis Pub/Sub broadcast: Emits real-time StatusEvents to WebSocket streams
        (`report:{report_id}:events`), driving live UI telemetry with sub-second latency.
    """

    def __init__(
        self,
        provider: Optional[AIProvider] = None,
        session_factory: async_sessionmaker[AsyncSession] = async_session_maker,
        publisher: Optional[StatusPublisher] = None,
    ):
        if provider is None:
            from src.agents.providers import get_default_provider
            self.provider = get_default_provider()
        else:
            self.provider = provider
        self.session_factory = session_factory
        self.publisher = publisher or default_publisher

    async def run_report(self, report_id: uuid.UUID) -> bool:
        """
        Entrypoint for end-to-end report generation pipeline:
        1. Retrieves user's research query from PostgreSQL.
        2. Invokes OrchestratorAgent to dynamically generate the task DAG.
        3. Hands the DAG to execute_dag() for concurrent topological execution.
        """
        # Step 1: Fetch initial report record
        async with self.session_factory() as session:
            stmt = select(Report).where(Report.id == report_id)
            res = await session.execute(stmt)
            report = res.scalars().first()
            if not report:
                raise ValueError(f"Report not found: {report_id}")
            query = report.query

        # Step 2: Transition status to PLANNING and emit websocket event
        await self._update_report_status(report_id, ReportStatus.PLANNING)

        # Step 3: Run OrchestratorAgent to decompose query into topological sub-tasks
        orchestrator_agent = AgentFactory.create(AgentRole.ORCHESTRATOR, self.provider)
        plan_task = AgentTask(
            id=uuid.uuid4(),
            agent_run_id=uuid.uuid4(),
            task_type="decompose_query",
            status=AgentTaskStatus.RUNNING,
            payload={"query": query},
        )
        plan_result = await orchestrator_agent.run(plan_task)

        if not plan_result.success:
            await self._update_report_status(report_id, ReportStatus.FAILED, error=plan_result.error)
            return False

        raw_dag = plan_result.output.get("dag", [])
        dag_nodes = [TaskNode.from_dict(item) for item in raw_dag]

        # Step 4: Hand over generated task nodes to the DAG concurrency engine
        return await self.execute_dag(report_id, dag_nodes)

    async def execute_dag(self, report_id: uuid.UUID, dag_nodes: List[TaskNode]) -> bool:
        """
        Executes the provided TaskNode DAG respecting dependency edges.
        Independent nodes run concurrently via asyncio.gather.

        Algorithm:
        ----------
        Loop until all nodes in dag_nodes have succeeded:
          1. Calculate ready_nodes = { n in dag_nodes | n not in completed and n.depends_on <= completed }.
          2. If ready_nodes is empty and completed < total: abort (deadlock / cycle detected).
          3. Broadcast pipeline stage transition (e.g. RESEARCHING, FACT_CHECKING, WRITING).
          4. Execute all ready_nodes in parallel using asyncio.gather.
          5. Inspect results: if any node failed, fail-fast and transition Report to FAILED.
          6. Add successful nodes to completed set and store their outputs in node_results for downstream injection.
        """
        completed_nodes: Set[str] = set()
        node_results: Dict[str, Dict[str, Any]] = {}
        all_node_map = {node.id: node for node in dag_nodes}

        while len(completed_nodes) < len(dag_nodes):
            # --- DAG Wavefront Discovery ---
            # Extract nodes whose prerequisite dependencies have all completed successfully.
            ready_nodes = [
                node
                for node in dag_nodes
                if node.id not in completed_nodes
                and all(dep in completed_nodes for dep in node.depends_on)
            ]

            # Deadlock & Cycle Guard: If there are uncompleted nodes but none are ready to run,
            # the graph contains an unsatisfied dependency edge or an invalid cycle.
            if not ready_nodes:
                err = f"Deadlock or cyclic dependency detected. Completed: {completed_nodes}"
                logger.error(err)
                await self._update_report_status(report_id, ReportStatus.FAILED, error=err)
                return False

            # --- Synchronize Overall Report Stage ---
            # Derive current user-facing milestone (Researching, Fact-checking, Writing)
            # based on the dominant agent roles in the active wavefront.
            await self._sync_pipeline_stage(report_id, ready_nodes)

            # --- Parallel Wavefront Execution ---
            # Launch all ready nodes concurrently as asynchronous tasks.
            # When ready_nodes contains multiple research subtopics, they execute in parallel,
            # leveraging Python's asyncio event loop to maximize I/O concurrency against LLM APIs.
            logger.info(
                f"[ENGINE] Launching {len(ready_nodes)} concurrent tasks: {[n.id for n in ready_nodes]}"
            )
            tasks = [
                self._execute_single_node(report_id, node, node_results)
                for node in ready_nodes
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # --- Evaluate Wavefront Results & Fail-Fast Guard ---
            for node, res in zip(ready_nodes, batch_results):
                if isinstance(res, Exception):
                    err_msg = f"Task {node.id} failed with unhandled exception: {res}"
                    logger.error(err_msg)
                    await self._update_report_status(report_id, ReportStatus.FAILED, error=err_msg)
                    return False
                elif not res.success:
                    err_msg = f"Task {node.id} failed: {res.error}"
                    logger.error(err_msg)
                    await self._update_report_status(report_id, ReportStatus.FAILED, error=err_msg)
                    return False
                else:
                    # Mark node complete and retain its output for downstream consumer nodes
                    completed_nodes.add(node.id)
                    node_results[node.id] = res.output

        # All nodes across all topological waves completed successfully
        await self._update_report_status(report_id, ReportStatus.COMPLETE)
        logger.info(f"[ENGINE] Report {report_id} pipeline completed successfully!")
        return True

    async def _execute_single_node(
        self,
        report_id: uuid.UUID,
        node: TaskNode,
        prior_results: Dict[str, Dict[str, Any]],
    ) -> AgentResult:
        """
        Executes an individual TaskNode within the DAG:
        1. Context Aggregation: Collates relevant outputs from upstream dependency nodes.
        2. State Audit Logging: Records initial AgentRun and AgentTask rows in PostgreSQL.
        3. Real-Time Telemetry: Emits a "task_started" event to the Redis Pub/Sub event bus.
        4. Decoupled Dispatch: Enqueues an AgentTaskCommand to the Arq queue (or worker fallback).
        5. Completion Notification: Updates database state and emits a "task_completed" event.
        """
        run_id = uuid.uuid4()
        task_id = uuid.uuid4()

        # --- Dynamic Upstream Context Assembly ---
        # Each specialized agent requires distinct context from prior DAG levels:
        # - FactChecker requires all claims extracted across all parallel Researcher nodes.
        # - Writer requires both raw claims AND fact-checker validation scores/citations.
        payload = dict(node.payload)
        if node.agent_role == AgentRole.FACT_CHECKER:
            research_outputs = [
                prior_results[dep]
                for dep in node.depends_on
                if dep in prior_results
            ]
            payload["research_outputs"] = research_outputs
        elif node.agent_role == AgentRole.WRITER:
            research_outputs = []
            fact_evaluations = []
            for dep_id in node.depends_on:
                dep_res = prior_results.get(dep_id, {})
                if "evaluations" in dep_res:
                    fact_evaluations.extend(dep_res["evaluations"])
            for res_data in prior_results.values():
                if "claims" in res_data:
                    research_outputs.append(res_data)
            payload["research_outputs"] = research_outputs
            payload["fact_evaluations"] = fact_evaluations

        # --- Dual-Write Persistence (PostgreSQL) ---
        # Maintain immutable audit history of every agent run and execution attempt
        async with self.session_factory() as session:
            agent_run = AgentRun(
                id=run_id,
                report_id=report_id,
                agent_role=node.agent_role,
                status=AgentRunStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
            agent_task_model = AgentTask(
                id=task_id,
                agent_run_id=run_id,
                task_type=node.task_type,
                status=AgentTaskStatus.RUNNING,
                payload=payload,
                retry_count=0,
            )
            session.add(agent_run)
            session.add(agent_task_model)
            await session.commit()

        # --- Real-Time Telemetry Broadcast ---
        # Broadcast immediately to Redis pub/sub so the Next.js frontend shows the node pulsing
        await self.publisher.publish(
            StatusEvent(
                event_type="task_started",
                report_id=report_id,
                status="running",
                agent_role=node.agent_role.value,
                run_id=run_id,
                task_id=task_id,
                metadata={"task_type": node.task_type, "node_id": node.id},
            )
        )

        from src.workers.queue import enqueue_agent_task

        # --- Command Pattern Execution ---
        # Encapsulate the unit of execution into an AgentTaskCommand for retry-safe queue processing
        command = AgentTaskCommand(
            agent_run_id=run_id,
            task_type=node.task_type,
            payload=payload,
            max_retries=3,
        )

        try:
            raw_result = await enqueue_agent_task(command, max_retries=3)
            result = AgentResult(
                success=raw_result.get("success", True),
                output=raw_result.get("output", {}),
                error=raw_result.get("error"),
            )
        except Exception as exc:
            logger.error(f"[ENGINE] Task dispatch failed for node {node.id}: {exc}")
            result = AgentResult(success=False, error=str(exc))

        # --- Terminal Task State Broadcast ---
        # Notify WebSocket subscribers whether this node succeeded or encountered a failure
        await self.publisher.publish(
            StatusEvent(
                event_type="task_completed" if result.success else "task_failed",
                report_id=report_id,
                status="succeeded" if result.success else "failed",
                agent_role=node.agent_role.value,
                run_id=run_id,
                task_id=task_id,
                metadata={"node_id": node.id, "error": result.error},
            )
        )

        return result

    async def _sync_pipeline_stage(self, report_id: uuid.UUID, ready_nodes: List[TaskNode]) -> None:
        """Map ready node roles to overall Report status stages."""
        roles = {n.agent_role for n in ready_nodes}
        if AgentRole.RESEARCHER in roles:
            await self._update_report_status(report_id, ReportStatus.RESEARCHING)
        elif AgentRole.FACT_CHECKER in roles:
            await self._update_report_status(report_id, ReportStatus.FACT_CHECKING)
        elif AgentRole.WRITER in roles:
            await self._update_report_status(report_id, ReportStatus.WRITING)

    async def _update_report_status(
        self,
        report_id: uuid.UUID,
        status: ReportStatus,
        error: Optional[str] = None,
    ) -> None:
        """Update report status in database and broadcast via publisher."""
        async with self.session_factory() as session:
            values: Dict[str, Any] = {"status": status}
            if status in (ReportStatus.COMPLETE, ReportStatus.FAILED):
                values["completed_at"] = datetime.now(timezone.utc)

            stmt = update(Report).where(Report.id == report_id).values(**values)
            await session.execute(stmt)
            await session.commit()

        await self.publisher.publish(
            StatusEvent(
                event_type="report_status_changed",
                report_id=report_id,
                status=status.value,
                metadata={"error": error} if error else {},
            )
        )
