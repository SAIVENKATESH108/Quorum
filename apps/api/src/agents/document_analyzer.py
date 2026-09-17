import logging
from typing import Any, Dict

from src.agents.base import Agent, AgentResult
from src.agents.providers import AIProvider
from src.db.models import AgentRole, AgentTask

logger = logging.getLogger("quorum.agents.document_analyzer")


class DocumentAnalysisAgent(Agent):
    """
    Analyzes codebases, repositories, and technical specifications to produce
    rigorous architecture documentation and research-paper-grade system writeups.
    """

    role: AgentRole = AgentRole.DOCUMENT_ANALYZER

    def __init__(self, provider: AIProvider):
        super().__init__(provider=provider)

    async def run(self, task: AgentTask) -> AgentResult:
        """
        Execute document and architecture analysis on provided repository or module payload.
        """
        payload: Dict[str, Any] = task.payload or {}
        repo_name = payload.get("repo_name", "Target Architecture")
        focus_area = payload.get("focus_area", "System Architecture & Core Protocols")
        file_tree = payload.get("file_tree", [])
        key_files = payload.get("key_files", [])

        # Format context for analysis
        files_summary = "\n".join([f"- {path}" for path in file_tree[:40]])
        sample_code = "\n\n".join([
            f"=== File: {f.get('path')} ===\n{f.get('content', '')[:1200]}"
            for f in key_files[:5]
        ])

        system_instruction = (
            "You are the Lead Systems Architect & Senior AI Research Fellow on the Quorum platform. "
            "Your objective is to inspect software architectures and synthesize institutional-grade "
            "technical papers and comprehensive engineering documentation. "
            "Maintain technical precision, formal terminology, clear ASCII/Mermaid structural descriptions, "
            "and cite specific file paths and module interactions."
        )

        prompt = (
            f"Synthesize a formal Technical Architecture Specification & Research Paper Section for:\n"
            f"Repository: {repo_name}\n"
            f"Focus Area: {focus_area}\n\n"
            f"Identified File Structure:\n{files_summary}\n\n"
            f"Key Module Excerpts:\n{sample_code}\n\n"
            f"Structure your response with:\n"
            f"1. Executive Abstract & Topological System Model\n"
            f"2. Core Abstractions, Interface Contracts & State Management\n"
            f"3. Algorithmic Complexity, Concurrency, & Fault-Tolerance Bounds\n"
            f"4. Concrete Getting Started & Deployment Recommendations\n"
        )

        try:
            raw_analysis = await self.provider.complete(prompt, system=system_instruction)

            return AgentResult(
                success=True,
                output={
                    "focus_area": focus_area,
                    "repo_name": repo_name,
                    "analysis": raw_analysis,
                    "module_count": len(file_tree),
                },
            )
        except Exception as exc:
            logger.exception(f"[DocumentAnalyzer] Failed analysis on {repo_name}: {exc}")
            return AgentResult(
                success=False,
                error_message=f"Document analysis failed: {exc}",
            )
