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

        total_files = payload.get("total_files", len(file_tree))
        is_tree_truncated = len(file_tree) < total_files or len(file_tree) >= 100
        is_files_truncated = len(key_files) < total_files

        # Format context for analysis
        files_summary = "\n".join([f"- {path}" for path in file_tree[:60]])
        if is_tree_truncated:
            files_summary += f"\n... [Truncated: {total_files} total files in repository, top 60 shown above]"

        sample_code = "\n\n".join([
            f"=== File: {f.get('path')} (Lines 1-{f.get('line_count', len(f.get('content', '').splitlines()))}) ===\n{f.get('content', '')[:2500]}"
            for f in key_files[:12]
        ])

        truncation_warning = ""
        if is_tree_truncated or is_files_truncated:
            truncation_warning = (
                f"IMPORTANT CONTEXT BOUNDARY: The repository contains {total_files} total files, but context budget limits "
                f"inspection to {len(key_files)} priority excerpts and {len(file_tree[:60])} tree entries. "
                "You MUST explicitly disclose this truncation in your writeup. "
                "You are STRICTLY FORBIDDEN from inferring, extrapolating, or inventing files, classes, or functions not present "
                "in the excerpts above. If an implementation detail is not visible in the provided code, state: "
                "'not determinable from the provided files'."
            )

        system_instruction = (
            "You are the Lead Systems Architect & Senior Code Reviewer on the Quorum platform. "
            "Your objective is to inspect software architectures and synthesize institutional-grade "
            "technical papers and comprehensive engineering documentation. "
            "CRITICAL GROUNDING RULES:\n"
            "1. ONLY describe files, functions, classes, and algorithms actually visible in the provided code excerpts and file tree.\n"
            "2. NEVER invent academic literature, DOIs, fictional dependencies, or unverified components.\n"
            "3. Cite exact file paths (e.g. `src/core/engine.py`) and exact symbols.\n"
            "4. If something is missing or not visible in the code excerpts, write 'not determinable from the provided files'.\n"
            "5. Maintain technical precision, formal terminology, and clear structural descriptions."
        )

        prompt = (
            f"Synthesize a formal Technical Architecture Specification for:\n"
            f"Repository: {repo_name}\n"
            f"Focus Area: {focus_area}\n\n"
            f"{truncation_warning}\n\n"
            f"Identified File Structure:\n{files_summary}\n\n"
            f"Key Module Excerpts:\n{sample_code}\n\n"
            f"Structure your response with:\n"
            f"1. Executive Abstract & Topological System Model (including explicit statement of files inspected vs total repo size)\n"
            f"2. Core Abstractions, Interface Contracts & State Management (strictly referencing real classes and functions)\n"
            f"3. Algorithmic Complexity, Concurrency, & Fault-Tolerance Bounds (grounded in actual code patterns, or marked as 'not determinable from the provided files')\n"
            f"4. Verified Component Directory (list of files inspected with their exact purpose)\n"
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
                    "key_files": key_files,
                    "file_tree": file_tree,
                    "is_truncated": is_tree_truncated or is_files_truncated,
                },
            )
        except Exception as exc:
            logger.exception(f"[DocumentAnalyzer] Failed analysis on {repo_name}: {exc}")
            return AgentResult(
                success=False,
                error_message=f"Document analysis failed: {exc}",
            )
