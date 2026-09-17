import json
import logging
from typing import Dict, List

from src.agents.base import Agent, AgentResult, TaskNode
from src.db.models import AgentRole, AgentTask

logger = logging.getLogger(__name__)


class OrchestratorAgent(Agent):
    """
    Decomposes a research query into a task DAG consisting of:
    - 3-6 independent parallel research subtopics
    - A fact-checking stage depending on all research subtopics
    - A writing/synthesis stage depending on the fact-checking stage
    """

    role = AgentRole.ORCHESTRATOR

    async def run(self, task: AgentTask) -> AgentResult:
        query = task.payload.get("query") if task.payload else None
        if not query:
            return AgentResult(success=False, error="Task payload missing 'query'")

        source_type = task.payload.get("source_type", "query") if task.payload else "query"
        source_ref = task.payload.get("source_ref") if task.payload else None

        # --- Branch A: Codebase & GitHub Repo Architecture Documentation Pipeline ---
        if source_type in ("github_repo", "local_folder"):
            repo_name = source_ref or query
            dag_nodes: List[TaskNode] = []
            analysis_node_ids: List[str] = []

            areas = [
                ("doc_arch", "System Architecture & Core Module Breakdown", "Analyze high-level topology, component boundaries, and module hierarchies"),
                ("doc_protocols", "State Synchronization, Concurrency & Protocols", "Analyze state machines, data flow, concurrency patterns, and event dispatch"),
                ("doc_complexity", "Algorithmic Complexity, Scaling & Design Patterns", "Analyze performance bounds, latency bottlenecks, and architectural design patterns"),
            ]

            for node_id, title, desc in areas:
                analysis_node_ids.append(node_id)
                dag_nodes.append(
                    TaskNode(
                        id=node_id,
                        description=f"Analyze: {title}",
                        task_type="document_analysis",
                        agent_role=AgentRole.DOCUMENT_ANALYZER,
                        depends_on=[],
                        payload={
                            "repo_name": repo_name,
                            "focus_area": title,
                            "description": desc,
                            "query": query,
                            "source_type": source_type,
                            "source_ref": source_ref,
                        },
                    )
                )

            fact_check_id = "fact_check_all"
            dag_nodes.append(
                TaskNode(
                    id=fact_check_id,
                    description="Verify code claims, validate architectural invariants, and compute confidence score",
                    task_type="fact_checking",
                    agent_role=AgentRole.FACT_CHECKER,
                    depends_on=list(analysis_node_ids),
                    payload={"query": f"Codebase Architecture Specification for {repo_name}"},
                )
            )

            write_id = "write_final_report"
            dag_nodes.append(
                TaskNode(
                    id=write_id,
                    description="Synthesize formal research paper & technical specification document with citations",
                    task_type="report_synthesis",
                    agent_role=AgentRole.WRITER,
                    depends_on=[fact_check_id],
                    payload={"query": f"Technical Architecture & Research Paper: {repo_name}"},
                )
            )

            dag_json = [node.to_dict() for node in dag_nodes]
            return AgentResult(
                success=True,
                output={
                    "query": query,
                    "source_type": source_type,
                    "dag": dag_json,
                    "node_count": len(dag_nodes),
                },
            )

        # --- Branch B: Standard Academic Research Synthesis Pipeline ---
        system_prompt = (
            "You are the Lead Research Orchestrator for Quorum, a multi-agent intelligence platform. "
            "Given a research topic, decompose it into 3 to 6 independent, complementary subtopics for investigation. "
            "Respond strictly in valid JSON format with a key 'subtopics' which is a list of objects containing "
            "'id' (e.g. 'subtopic_1'), 'title', and 'description'."
        )

        prompt = (
            f"Decompose the following research topic into 3 to 6 distinct subtopics for parallel research:\n"
            f"Topic: \"{query}\"\n\n"
            f"Ensure subtopics are mutually exclusive and collectively exhaustive."
        )

        try:
            llm_response = await self.provider.complete(prompt, system=system_prompt)
            subtopics = self._parse_subtopics(llm_response, query)
        except Exception as exc:
            logger.warning(f"Failed to obtain LLM decomposition, using fallback subtopics: {exc}")
            subtopics = self._default_subtopics(query)

        # Build task DAG nodes
        dag_nodes: List[TaskNode] = []
        research_node_ids: List[str] = []

        # 1. Independent Research Nodes (Parallel Execution)
        for idx, sub in enumerate(subtopics, 1):
            node_id = f"research_{idx}"
            research_node_ids.append(node_id)
            dag_nodes.append(
                TaskNode(
                    id=node_id,
                    description=f"Research: {sub['title']}",
                    task_type="research_subtopic",
                    agent_role=AgentRole.RESEARCHER,
                    depends_on=[],  # No dependencies -> runs concurrently
                    payload={
                        "query": query,
                        "subtopic_id": node_id,
                        "title": sub["title"],
                        "description": sub.get("description", ""),
                    },
                )
            )

        # 2. Fact Checking Stage (Depends on all research nodes)
        fact_check_id = "fact_check_all"
        dag_nodes.append(
            TaskNode(
                id=fact_check_id,
                description="Cross-reference claims, detect contradictions, and assign confidence scores",
                task_type="fact_checking",
                agent_role=AgentRole.FACT_CHECKER,
                depends_on=list(research_node_ids),
                payload={"query": query},
            )
        )

        # 3. Final Writing & Synthesis Stage (Depends on fact checking)
        write_id = "write_final_report"
        dag_nodes.append(
            TaskNode(
                id=write_id,
                description="Synthesize verified findings into structured report sections with citations",
                task_type="report_synthesis",
                agent_role=AgentRole.WRITER,
                depends_on=[fact_check_id],
                payload={"query": query},
            )
        )

        dag_json = [node.to_dict() for node in dag_nodes]
        return AgentResult(
            success=True,
            output={
                "query": query,
                "subtopics_count": len(subtopics),
                "dag": dag_json,
                "node_count": len(dag_nodes),
            },
        )

    def _parse_subtopics(self, text: str, query: str) -> List[Dict[str, str]]:
        """Parse structured subtopics from JSON response."""
        try:
            # Strip markdown block formatting if present
            clean = text.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            data = json.loads(clean.strip())
            if isinstance(data, dict) and "subtopics" in data and isinstance(data["subtopics"], list):
                return data["subtopics"]
        except Exception:
            pass
        return self._default_subtopics(query)

    def _default_subtopics(self, query: str) -> List[Dict[str, str]]:
        return [
            {
                "title": "Core Foundations & Architecture",
                "description": f"Historical development, fundamental principles, and structural paradigms related to: {query[:200]}",
            },
            {
                "title": "Empirical Performance & Benchmarks",
                "description": f"Quantitative analysis, real-world deployments, and comparative metrics for: {query[:200]}",
            },
            {
                "title": "Security, Scalability & Risk",
                "description": f"Vulnerability surfaces, failure modes, consensus overhead, and governance in: {query[:200]}",
            },
            {
                "title": "Future Outlook & Next Frontiers",
                "description": f"Emerging trends, integration with adjacent systems, and strategic projections for: {query[:200]}",
            },
        ]
