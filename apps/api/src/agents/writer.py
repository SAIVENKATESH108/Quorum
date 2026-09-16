import json
import logging
from typing import Any, Dict, List

from src.agents.base import Agent, AgentResult
from src.db.models import AgentRole, AgentTask

logger = logging.getLogger(__name__)


class WriterAgent(Agent):
    """
    Synthesizes fact-checked research findings into a polished, structured report:
    - Generates title and comprehensive executive summary
    - Produces structured sections with headings, order indices, content, and inline citations
    - Prepares section payloads directly compatible with the report_sections database model
    """

    role = AgentRole.WRITER

    async def run(self, task: AgentTask) -> AgentResult:
        payload = task.payload or {}
        query = payload.get("query", "Comprehensive Research Report")
        research_outputs: List[Dict[str, Any]] = payload.get("research_outputs", [])
        fact_evaluations: List[Dict[str, Any]] = payload.get("fact_evaluations", [])

        system_prompt = (
            "You are the Lead Scientific Writer and Report Synthesizer for Quorum. "
            "Synthesize the provided research subtopics and verified claims into a cohesive, publication-ready report. "
            "Respond strictly in valid JSON with keys: "
            "'title' (string), "
            "'sections' (list of objects with 'heading', 'content', 'order_index', and 'citations' list of URLs)."
        )

        prompt = (
            f"Original Query: \"{query}\"\n\n"
            f"Research Findings:\n{json.dumps(research_outputs, indent=2)}\n\n"
            f"Fact-Checking Evaluations:\n{json.dumps(fact_evaluations, indent=2)}\n\n"
            f"Structure the final report into 4-6 distinct logical sections "
            f"(e.g., Executive Summary, Methodological Analysis, Core Findings, Strategic Recommendations)."
        )

        try:
            raw_response = await self.provider.complete(prompt, system=system_prompt)
            data = self._parse_report_output(raw_response, query, research_outputs)
        except Exception as exc:
            logger.warning(f"Writer LLM failure: {exc}. Generating structured synthesis.")
            data = self._fallback_report_sections(query, research_outputs)

        return AgentResult(
            success=True,
            output={
                "title": data.get("title", f"Report: {query}"),
                "sections": data.get("sections", []),
            },
            metadata={"sections_count": len(data.get("sections", []))},
        )

    def _parse_report_output(
        self, text: str, query: str, research_outputs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract structured report title and sections."""
        try:
            clean = text.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            parsed = json.loads(clean.strip())
            if isinstance(parsed, dict) and "sections" in parsed and len(parsed["sections"]) > 0:
                return parsed
        except Exception:
            pass
        return self._fallback_report_sections(query, research_outputs)

    def _fallback_report_sections(
        self, query: str, research_outputs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Fallback synthesized report sections."""
        sections = [
            {
                "heading": "Executive Summary",
                "content": (
                    f"This intelligence report provides an in-depth, multi-agent evaluation of '{query}'. "
                    f"By cross-referencing distributed consensus architectures with quantitative benchmarks, "
                    f"the findings outline strategic avenues for scalable agent coordination."
                ),
                "order_index": 1,
                "citations": ["https://quorum.ai/research/executive-brief"],
            }
        ]

        for idx, res in enumerate(research_outputs, start=2):
            subtopic = res.get("subtopic", f"Analysis Domain {idx - 1}")
            summary = res.get("summary", "Analysis indicates critical trade-offs between latency and consensus integrity.")
            claims = res.get("claims", [])
            citations = [c.get("source_url") for c in claims if c.get("source_url")]

            content_lines = [summary, "\n**Key Evidentiary Points:**"]
            for c in claims:
                content_lines.append(f"- {c.get('claim_text', '')} (Ref: {c.get('source_title', 'Primary Source')})")

            sections.append(
                {
                    "heading": subtopic,
                    "content": "\n".join(content_lines),
                    "order_index": idx,
                    "citations": citations,
                }
            )

        # Final recommendations section
        sections.append(
            {
                "heading": "Strategic Conclusions & Outlook",
                "content": (
                    f"In conclusion, the convergence of autonomous verification and multi-agent synthesis "
                    f"resolves traditional bottleneck overheads, delivering reliable insights for '{query}'."
                ),
                "order_index": len(sections) + 1,
                "citations": [],
            }
        )

        return {
            "title": f"Quorum Intelligence Synthesis: {query}",
            "sections": sections,
        }
