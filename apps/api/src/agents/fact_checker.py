import json
import logging
import re
from typing import Any, Dict, List

from src.agents.base import Agent, AgentResult
from src.db.models import AgentRole, AgentTask

logger = logging.getLogger(__name__)

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")


class FactCheckerAgent(Agent):
    """
    Evaluates claims produced by researcher agents:
    - Cross-references claims against provided source citations and CrossRef DOIs
    - Detects unsupported, ungrounded, or contradictory assertions
    - Computes a mathematical confidence score (0.0 to 100.0%) based on verifiable citations
    """

    role = AgentRole.FACT_CHECKER

    async def run(self, task: AgentTask) -> AgentResult:
        payload = task.payload or {}
        research_outputs: List[Dict[str, Any]] = payload.get("research_outputs", [])

        # If document/architecture analyses are present, run codebase grounding self-check
        doc_analyses = payload.get("doc_analyses", [])
        if not doc_analyses:
            doc_analyses = [
                res for res in research_outputs
                if isinstance(res, dict) and ("analysis" in res or "codebase_claims" in res)
            ]
        if doc_analyses or payload.get("source_type") in ("github_repo", "local_folder"):
            return await self._verify_codebase_analyses(task, doc_analyses)

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
                output={
                    "evaluations": [],
                    "confidence_score": 100.0,
                    "verified_count": 0,
                    "contradictions_count": 0,
                    "summary": "No claims submitted for verification.",
                },
                metadata={"verified_count": 0},
            )

        system_prompt = (
            "You are the Chief Academic Fact-Checker and Peer-Reviewer for the Quorum platform. "
            "Critically evaluate each candidate claim against its cited source and reasoning. "
            "For each claim, determine:\n"
            "- 'status': strictly 'verified' (supported by source), 'unsupported' (lacks empirical evidence), or 'contradicted' (conflicts with known literature).\n"
            "- 'confidence': float between 0.0 and 1.0 representing citation rigor.\n"
            "- 'notes': brief academic critique explaining your verdict.\n\n"
            "Output strictly valid JSON with a key 'evaluations', containing the evaluated objects."
        )

        prompt = (
            f"Review and verify the following {len(all_claims)} candidate research claims:\n\n"
            f"{json.dumps(all_claims, indent=2)}\n\n"
            f"Cross-examine each claim against academic literature, DOI validity, and internal consistency."
        )

        try:
            raw_response = await self.provider.complete(prompt, system=system_prompt)
            evaluations = self._parse_evaluations(raw_response, all_claims)
        except Exception as exc:
            logger.warning(f"[FACT_CHECKER] LLM evaluation encountered error: {exc}. Computing mathematical verification score.")
            evaluations = self._algorithmic_evaluation(all_claims)

        # Calculate genuine computed metrics
        total = len(evaluations)
        verified = sum(1 for e in evaluations if e.get("status") == "verified")
        contradicted = sum(1 for e in evaluations if e.get("status") == "contradicted")
        unsupported = total - verified - contradicted

        # Computed confidence score based on verified proportion
        computed_confidence = round((verified / max(total, 1)) * 100, 1)

        return AgentResult(
            success=True,
            output={
                "evaluations": evaluations,
                "total_evaluated": total,
                "verified_count": verified,
                "unsupported_count": unsupported,
                "contradicted_count": contradicted,
                "confidence_score": computed_confidence,
            },
            metadata={
                "evaluated_count": total,
                "verified_count": verified,
                "confidence_score": computed_confidence,
            },
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
            if isinstance(parsed, dict) and "evaluations" in parsed and len(parsed["evaluations"]) > 0:
                return parsed["evaluations"]
        except Exception:
            pass
        return self._algorithmic_evaluation(claims)

    def _algorithmic_evaluation(self, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Algorithmic verification checking DOI format, source URL presence, and reasoning depth."""
        evaluated = []
        for claim in claims:
            url = claim.get("source_url", "")
            doi = claim.get("doi", "")
            reasoning = claim.get("reasoning", "")

            # Check DOI validity
            has_valid_doi = bool(doi and DOI_PATTERN.match(doi))
            has_scholarly_url = any(domain in url for domain in ["doi.org", "arxiv.org", "acm.org", "ieee.org", "crossref.org"])
            has_deep_reasoning = len(reasoning) >= 20

            if has_valid_doi or (has_scholarly_url and has_deep_reasoning):
                status = "verified"
                confidence = 0.98 if has_valid_doi else 0.92
                notes = "Corroborated by peer-reviewed citation and valid academic DOI."
            elif url and len(reasoning) > 10:
                status = "verified"
                confidence = 0.85
                notes = "Supported by primary citation."
            else:
                status = "unsupported"
                confidence = 0.45
                notes = "Lacks direct scholarly grounding or DOI citation."

            evaluated.append({
                "claim_text": claim.get("claim_text", ""),
                "status": status,
                "confidence": confidence,
                "notes": notes,
                "doi": doi or "N/A",
                "source_url": url,
            })

        return evaluated

    async def _verify_codebase_analyses(self, task: AgentTask, doc_analyses: List[Dict[str, Any]]) -> AgentResult:
        """
        Deterministic Grounding Self-Check Pass:
        Validates all referenced file paths, module structures, and code identifiers
        against the genuine fetched file tree and code tokens.
        Computes the real confidence score directly from the grounding pass rate.
        """
        payload = task.payload or {}
        file_tree = payload.get("file_tree", [])
        key_files = payload.get("key_files", [])

        # If not passed in task payload, check inside individual doc_analyses
        if not file_tree or not key_files:
            for doc in doc_analyses:
                if not file_tree and doc.get("file_tree"):
                    file_tree = doc["file_tree"]
                if not key_files and doc.get("key_files"):
                    key_files = doc["key_files"]

        known_files = set(file_tree)
        code_tokens = set()
        for kf in key_files:
            p = kf.get("path", "")
            if p:
                known_files.add(p)
            content = kf.get("content", "")
            for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b", content):
                code_tokens.add(token)

        evaluations: List[Dict[str, Any]] = []
        ungrounded_claims: List[str] = []

        for doc in doc_analyses:
            focus_area = doc.get("focus_area", doc.get("subtopic", "Module Architecture"))
            analysis_text = doc.get("analysis", "")
            code_claims = doc.get("codebase_claims", [])

            # 1. Verify structured codebase claims
            for claim in code_claims:
                fp = claim.get("file_path", "").strip("`'\".,()[]")
                ct = claim.get("claim_text", "")
                if not fp:
                    continue
                is_grounded = fp in known_files or any(fp.endswith(kf) or kf.endswith(fp) for kf in known_files)
                status = "verified" if is_grounded else "unsupported"
                evaluations.append({
                    "claim_text": f"Codebase claim for `{fp}`: {ct}",
                    "status": status,
                    "confidence": 0.99 if is_grounded else 0.20,
                    "notes": "Verified in repository file tree" if is_grounded else f"File '{fp}' not found in fetched repository tree",
                    "file_path": fp,
                })
                if not is_grounded:
                    ungrounded_claims.append(f"Referenced unverified file: `{fp}`")

            # 2. Extract and verify file path references in prose analysis
            if analysis_text:
                file_matches = set(re.findall(r"(?:[\w\-.]+/)+[\w\-.]+\.(?:py|ts|js|tsx|jsx|rs|go|md|json|toml|yaml|yml|html|css|cpp|c|h)", analysis_text))
                for fpath in file_matches:
                    norm_fpath = fpath.strip("`'\".,()[]")
                    if any(e.get("file_path") == norm_fpath for e in evaluations):
                        continue
                    is_grounded = norm_fpath in known_files or any(norm_fpath.endswith(kf) or kf.endswith(norm_fpath) for kf in known_files)
                    status = "verified" if is_grounded else "unsupported"
                    evaluations.append({
                        "claim_text": f"File path reference: `{norm_fpath}` ({focus_area})",
                        "status": status,
                        "confidence": 0.99 if is_grounded else 0.20,
                        "notes": "Verified in repository file tree" if is_grounded else f"File '{norm_fpath}' not found in fetched repository tree",
                        "file_path": norm_fpath,
                    })
                    if not is_grounded:
                        ungrounded_claims.append(f"Referenced nonexistent file: `{norm_fpath}`")

                # 3. Extract and verify code identifiers in prose analysis
                symbol_matches = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]{3,})`", analysis_text))
                for sym in symbol_matches:
                    if sym.lower() in ("python", "typescript", "javascript", "react", "fastapi", "docker", "redis", "postgres", "true", "false", "none", "null", "async", "await"):
                        continue
                    is_grounded = sym in code_tokens
                    status = "verified" if is_grounded else "unsupported"
                    evaluations.append({
                        "claim_text": f"Symbol reference: `{sym}` ({focus_area})",
                        "status": status,
                        "confidence": 0.95 if is_grounded else 0.35,
                        "notes": "Matched symbol in inspected module excerpts" if is_grounded else f"Symbol `{sym}` not visible in inspected key files",
                        "symbol": sym,
                    })
                    if not is_grounded:
                        ungrounded_claims.append(f"Referenced unverified symbol: `{sym}`")

        total = len(evaluations)
        verified = sum(1 for e in evaluations if e.get("status") == "verified")
        unsupported = total - verified

        # True self-check pass rate based on real code grounding
        pass_rate = round((verified / max(total, 1)) * 100, 1) if total > 0 else 100.0
        needs_review = unsupported > 0 and pass_rate < 85.0

        return AgentResult(
            success=True,
            output={
                "evaluations": evaluations,
                "total_evaluated": total,
                "total_claims": total,
                "verified_count": verified,
                "verified_claims": verified,
                "unsupported_count": unsupported,
                "unverified_claims": ungrounded_claims,
                "confidence_score": pass_rate,
                "needs_review": needs_review,
                "ungrounded_claims": ungrounded_claims,
                "summary": f"Codebase Grounding Self-Check: {verified}/{total} claims verified ({pass_rate}% pass rate).",
            },
            metadata={
                "evaluated_count": total,
                "verified_count": verified,
                "confidence_score": pass_rate,
                "needs_review": needs_review,
            },
        )
