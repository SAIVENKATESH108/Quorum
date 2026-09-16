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
    Core Multi-Agent Orchestration Engine:
    - Accepts report_id and the DAG produced by OrchestratorAgent
    - Executes independent nodes concurrently using asyncio.gather (parallel research agents)
    - Waits for all dependencies of a node to reach "succeeded" before dispatching
    - Publishes state transitions after every step via StatusPublisher
    - Transitions reports.status: planning -> researching -> fact_checking -> writing -> complete
    """

    def __init__(
        self,
        provider: AIProvider,
        session_factory: async_sessionmaker[AsyncSession] = async_session_maker,
        publisher: Optional[StatusPublisher] = None,
    ):
        self.provider = provider
        self.session_factory = session_factory
        self.publisher = publisher or default_publisher

    async def run_report(self, report_id: uuid.UUID) -> bool:
        """Full pipeline runner: decomposes query into DAG and orchestrates to completion."""
        # 1. Fetch Report query
        async with self.session_factory() as session:
            stmt = select(Report).where(Report.id == report_id)
            res = await session.execute(stmt)
            report = res.scalars().first()
            if not report:
                raise ValueError(f"Report not found: {report_id}")
            query = report.query

        # 2. Stage: Planning
        await self._update_report_status(report_id, ReportStatus.PLANNING)

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

        # 3. Execute DAG
        return await self.execute_dag(report_id, dag_nodes)

    async def execute_dag(self, report_id: uuid.UUID, dag_nodes: List[TaskNode]) -> bool:
        """
        Executes the provided TaskNode DAG respecting dependency edges.
        Independent nodes run concurrently via asyncio.gather.
        """
        completed_nodes: Set[str] = set()
        node_results: Dict[str, Dict[str, Any]] = {}
        all_node_map = {node.id: node for node in dag_nodes}

        while len(completed_nodes) < len(dag_nodes):
            # Find nodes ready to execute: not completed, and all dependencies in completed_nodes
            ready_nodes = [
                node
                for node in dag_nodes
                if node.id not in completed_nodes
                and all(dep in completed_nodes for dep in node.depends_on)
            ]

            if not ready_nodes:
                err = f"Deadlock or cyclic dependency detected. Completed: {completed_nodes}"
                logger.error(err)
                await self._update_report_status(report_id, ReportStatus.FAILED, error=err)
                return False

            # Update report status based on current active stage
            await self._sync_pipeline_stage(report_id, ready_nodes)

            # Concurrent execution of all ready nodes
            logger.info(
                f"[ENGINE] Launching {len(ready_nodes)} concurrent tasks: {[n.id for n in ready_nodes]}"
            )
            tasks = [
                self._execute_single_node(report_id, node, node_results)
                for node in ready_nodes
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Evaluate batch outcomes
            for node, res in zip(ready_nodes, batch_results):
                if isinstance(res, Exception):
                    err_msg = f"Task {node.id} failed with exception: {res}"
                    logger.error(err_msg)
                    await self._update_report_status(report_id, ReportStatus.FAILED, error=err_msg)
                    return False
                elif not res.success:
                    err_msg = f"Task {node.id} failed: {res.error}"
                    logger.error(err_msg)
                    await self._update_report_status(report_id, ReportStatus.FAILED, error=err_msg)
                    return False
                else:
                    completed_nodes.add(node.id)
                    node_results[node.id] = res.output

        # All nodes completed successfully -> Mark report complete
        await self._update_report_status(report_id, ReportStatus.COMPLETE)
        logger.info(f"[ENGINE] Report {report_id} pipeline completed successfully!")
        return True

    async def _execute_single_node(
        self,
        report_id: uuid.UUID,
        node: TaskNode,
        prior_results: Dict[str, Dict[str, Any]],
    ) -> AgentResult:
        """Executes a single task node with retries, database persistence, and pub/sub events."""
        run_id = uuid.uuid4()
        task_id = uuid.uuid4()

        # Augment payload with results from upstream dependencies
        payload = dict(node.payload)
        if node.agent_role == AgentRole.FACT_CHECKER:
            research_outputs = [
                prior_results[dep]
                for dep in node.depends_on
                if dep in prior_results
            ]
            payload["research_outputs"] = research_outputs
        elif node.agent_role == AgentRole.WRITER:
            # Provide fact checker evaluations and researcher findings
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

        # Create AgentRun and AgentTask in DB
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

        # Publish task started event
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

        # Publish task completed event
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
