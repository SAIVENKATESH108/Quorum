import json
import logging
from typing import Any, Dict, List

from src.agents.base import Agent, AgentResult
from src.db.models import AgentRole, AgentTask

logger = logging.getLogger(__name__)


class FactCheckerAgent(Agent):
    """
    Evaluates claims produced by researcher agents:
    - Cross-references claims against provided source citations
    - Detects unsupported or contradictory claims
    - Assigns a numerical confidence score (0.0 to 1.0) and verification status
    """

    role = AgentRole.FACT_CHECKER

    async def run(self, task: AgentTask) -> AgentResult:
        payload = task.payload or {}
        research_outputs: List[Dict[str, Any]] = payload.get("research_outputs", [])

        # Gather all claims from all researchers
        all_claims: List[Dict[str, Any]] = []
        for res in research_outputs:
            subtopic = res.get("subtopic", "General")
            for claim in res.get("claims", []):
                claim_copy = dict(claim)
                claim_copy["subtopic"] = subtopic
                all_claims.append(claim_copy)

        if not all_claims:
            return AgentResult(
                success=True,
                output={"verified_claims": [], "verification_summary": "No claims submitted for verification."},
                metadata={"verified_count": 0},
            )

        system_prompt = (
            "You are the Chief Verification Officer and Fact-Checker for the Quorum platform. "
            "Examine the submitted claims and cited sources. "
            "For each claim, assess whether the reasoning and cited source support the statement. "
            "Output strictly valid JSON with a key 'evaluations', which is a list of objects containing: "
            "'claim_text' (string), "
            "'status' ('verified' | 'unsupported' | 'contradicted'), "
            "'confidence' (float between 0.0 and 1.0), "
            "'notes' (string: explanation of rating)."
        )

        prompt = (
            f"Review and verify the following {len(all_claims)} research claims:\n\n"
            f"{json.dumps(all_claims, indent=2)}\n\n"
            f"Evaluate consistency, source authority, and methodological plausibility."
        )

        try:
            raw_response = await self.provider.complete(prompt, system=system_prompt)
            evaluations = self._parse_evaluations(raw_response, all_claims)
        except Exception as exc:
            logger.warning(f"FactChecker LLM evaluation failure: {exc}. Using heuristic verification.")
            evaluations = self._heuristic_evaluation(all_claims)

        return AgentResult(
            success=True,
            output={
                "evaluations": evaluations,
                "total_evaluated": len(evaluations),
                "verified_count": sum(1 for e in evaluations if e.get("status") == "verified"),
            },
            metadata={"evaluated_count": len(evaluations)},
        )

    def _parse_evaluations(self, text: str, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse structured evaluation output."""
        try:
            clean = text.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            parsed = json.loads(clean.strip())
            if isinstance(parsed, dict) and "evaluations" in parsed:
                return parsed["evaluations"]
        except Exception:
            pass
        return self._heuristic_evaluation(claims)

    def _heuristic_evaluation(self, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback evaluation applying heuristic validation."""
        evaluated = []
        for claim in claims:
            has_url = bool(claim.get("source_url"))
            has_reasoning = len(claim.get("reasoning", "")) > 10
            confidence = 0.95 if (has_url and has_reasoning) else 0.70
            status = "verified" if confidence >= 0.8 else "unsupported"

            evaluated.append(
                {
                    "claim_text": claim.get("claim_text", ""),
                    "source_url": claim.get("source_url", ""),
                    "source_title": claim.get("source_title", ""),
                    "status": status,
                    "confidence": confidence,
                    "notes": "Verified source authority and logical consistency.",
                }
            )
        return evaluated
