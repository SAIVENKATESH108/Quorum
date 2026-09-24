import pytest
from src.agents.providers import OllamaProvider, get_default_provider
from src.services.github_connector import GitHubConnector
from src.agents.document_analyzer import DocumentAnalysisAgent
from src.agents.plugins import MCPPluginRegistry, AcademicDOIVerifierPlugin
from src.db.models import AgentRole, AgentTask


@pytest.mark.asyncio
async def test_ollama_provider_configuration():
    """Verify OllamaProvider initializes with offline base URL and model defaults."""
    provider = OllamaProvider(model="llama3")
    assert provider.name == "Ollama"
    assert "11434" in provider.base_url
    assert provider.model == "llama3"

    # Verify get_default_provider in offline mode returns OllamaProvider directly
    local_chain = get_default_provider(mode="local")
    assert isinstance(local_chain, OllamaProvider)


@pytest.mark.asyncio
async def test_github_connector_url_parsing():
    """Verify GitHubConnector parses standard repo URLs and owner/repo shorthand."""
    owner, repo = GitHubConnector.parse_repo_url("https://github.com/facebook/react")
    assert owner == "facebook"
    assert repo == "react"

    owner2, repo2 = GitHubConnector.parse_repo_url("astral-sh/uv.git")
    assert owner2 == "astral-sh"
    assert repo2 == "uv"


@pytest.mark.asyncio
async def test_document_analyzer_agent_execution():
    """Verify DocumentAnalysisAgent processes codebase payload and produces structured architecture paper."""
    from unittest.mock import AsyncMock
    provider = AsyncMock()
    provider.complete = AsyncMock(
        return_value="### 1. Executive Abstract\nFormal architecture synthesis of Quorum codebase."
    )
    agent = DocumentAnalysisAgent(provider=provider)
    assert agent.role == AgentRole.DOCUMENT_ANALYZER

    task = AgentTask(
        task_type="document_analysis",
        payload={
            "repo_name": "Quorum",
            "focus_area": "System Architecture & Core Protocols",
            "file_tree": ["src/main.py", "src/agents/engine.py", "README.md"],
            "key_files": [{"path": "README.md", "content": "# Quorum Platform"}],
        },
    )

    result = await agent.run(task)
    assert result.success is True
    assert "analysis" in result.output
    assert result.output["repo_name"] == "Quorum"


@pytest.mark.asyncio
async def test_mcp_plugin_registry_and_doi_verifier():
    """Verify MCPPluginRegistry registers tool servers and AcademicDOIVerifierPlugin verifies citations."""
    plugins = MCPPluginRegistry.list_plugins()
    assert len(plugins) >= 1
    assert any(p["plugin_id"] == "academic-doi-verifier" for p in plugins)

    provider = get_default_provider()
    verifier = AcademicDOIVerifierPlugin(provider=provider)

    task = AgentTask(
        task_type="verify_citations",
        payload={
            "sources": [
                {"url": "https://dl.acm.org/doi/10.1145/571637.571640"},
                {"url": "https://arxiv.org/abs/2201.05677"},
            ]
        },
    )

    result = await verifier.run(task)
    assert result.success is True
    assert result.output["count"] == 2
    assert all(c["verified"] is True for c in result.output["verified_citations"])


@pytest.mark.asyncio
async def test_scan_local_directory(tmp_path):
    """Verify GitHubConnector.scan_local_directory inspects and reads real local files."""
    test_file = tmp_path / "main.py"
    test_file.write_text("def run():\n    return 'quorum'", encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text("# Test Repo\nLocal workspace.", encoding="utf-8")

    result = GitHubConnector.scan_local_directory(str(tmp_path))
    assert result["owner"] == "local"
    assert result["total_files"] == 2
    assert "main.py" in result["file_paths"]
    assert "README.md" in result["file_paths"]
    assert any(f["path"] == "main.py" for f in result["key_files"])


@pytest.mark.asyncio
async def test_orchestrator_preserves_code_context():
    """Verify OrchestratorAgent forwards file_tree and key_files into child DAG nodes."""
    from src.agents.orchestrator import OrchestratorAgent
    from unittest.mock import AsyncMock
    provider = AsyncMock()
    orchestrator = OrchestratorAgent(provider=provider)

    task = AgentTask(
        task_type="decompose_query",
        payload={
            "query": "Document Quorum",
            "source_type": "local_folder",
            "source_ref": "d:/test",
            "file_tree": ["src/main.py", "README.md"],
            "key_files": [{"path": "README.md", "content": "# Quorum"}],
        },
    )

    result = await orchestrator.run(task)
    assert result.success is True
    dag = result.output["dag"]
    assert len(dag) > 0
    # Verify child document_analysis nodes received the real code payload
    for node in dag:
        if node["agent_role"] == "document_analyzer":
            assert node["payload"]["file_tree"] == ["src/main.py", "README.md"]
            assert len(node["payload"]["key_files"]) == 1


@pytest.mark.asyncio
async def test_fact_checker_codebase_grounding_pass_rate_and_review():
    """Verify FactCheckerAgent calculates confidence_score directly from pass rate and flags needs_review."""
    from src.agents.fact_checker import FactCheckerAgent
    from unittest.mock import AsyncMock

    provider = AsyncMock()
    agent = FactCheckerAgent(provider=provider)

    doc_analyses = [
        {
            "subtopic": "Core Engine",
            "codebase_claims": [
                {
                    "file_path": "src/main.py",
                    "claim_text": "Exposes FastAPI application and configures routes",
                },
                {
                    "file_path": "src/engine.py",
                    "claim_text": "Implements DAG execution engine for concurrent agents",
                },
                {
                    "file_path": "src/nonexistent_fake_module.py",
                    "claim_text": "Contains imaginary quantum neural network scheduler",
                },
            ],
        }
    ]

    task = AgentTask(
        task_type="fact_check",
        payload={
            "doc_analyses": doc_analyses,
            "file_tree": ["src/main.py", "src/engine.py", "README.md"],
            "key_files": [
                {"path": "src/main.py", "content": "from fastapi import FastAPI\napp = FastAPI()"},
                {"path": "src/engine.py", "content": "class OrchestrationEngine:\n    async def execute_dag(): pass"},
            ],
        },
    )

    result = await agent.run(task)
    assert result.success is True
    out = result.output
    # 2 out of 3 claims should be verified
    assert out["total_claims"] == 3
    assert out["confidence_score"] == pytest.approx(66.7, rel=1e-1)
    assert out["needs_review"] is True
    assert len(out["unverified_claims"]) == 1
    assert "src/nonexistent_fake_module.py" in str(out["unverified_claims"])


@pytest.mark.asyncio
async def test_writer_agent_codebase_synthesis_and_blob_urls():
    """Verify WriterAgent in codebase mode uses GitHub blob URLs with line ranges and rejects fake DOIs."""
    from src.agents.writer import WriterAgent
    from unittest.mock import AsyncMock

    provider = AsyncMock()
    writer = WriterAgent(provider=provider)

    key_files = [
        {
            "path": "src/main.py",
            "blob_url": "https://github.com/astral-sh/uv/blob/main/src/main.py",
            "line_count": 85,
        },
        {
            "path": "src/engine.py",
            "blob_url": "https://github.com/astral-sh/uv/blob/main/src/engine.py",
            "line_count": 120,
        },
    ]

    doc_analyses = [
        {
            "subtopic": "Architecture & Engine",
            "summary": "The codebase features an asynchronous task engine.",
            "codebase_claims": [
                {"file_path": "src/main.py", "claim_text": "Initializes FastAPI router"}
            ],
        }
    ]

    task = AgentTask(
        task_type="write_report",
        payload={
            "query": "astral-sh/uv",
            "source_type": "github_repo",
            "key_files": key_files,
            "file_tree": ["src/main.py", "src/engine.py"],
            "doc_analyses": doc_analyses,
            "confidence_score": 1.0,
            "needs_review": False,
        },
    )

    result = await writer.run(task)
    assert result.success is True
    sections = result.output["sections"]
    assert len(sections) >= 3

    # Check citations: must be real blob URLs with line ranges, no academic DOIs
    all_citations = [c for sec in sections for c in sec.get("citations", [])]
    assert len(all_citations) > 0
    for cite in all_citations:
        assert cite.startswith("https://github.com/astral-sh/uv/blob/main/")
        assert "#L1-L" in cite
        assert "doi.org" not in cite


@pytest.mark.asyncio
async def test_writer_agent_self_check_does_not_strip_prose():
    """Verify that ungrounded references in sections are NOT silently stripped, but trigger needs_review callout."""
    from src.agents.writer import WriterAgent
    from unittest.mock import AsyncMock

    provider = AsyncMock()
    # Mock LLM producing an ungrounded hallucination referencing a fake file
    provider.complete = AsyncMock(
        return_value='''{
            "title": "Architecture Specification",
            "sections": [
                {
                    "heading": "1. Executive Summary",
                    "content": "The system processes data using fake_crypto_layer.rs for end to end encryption.",
                    "order_index": 1,
                    "citations": ["https://github.com/owner/repo/blob/main/src/main.rs#L1-L50"]
                }
            ]
        }'''
    )
    writer = WriterAgent(provider=provider)

    task = AgentTask(
        task_type="write_report",
        payload={
            "query": "owner/repo",
            "source_type": "github_repo",
            "key_files": [{"path": "src/main.rs", "blob_url": "https://github.com/owner/repo/blob/main/src/main.rs", "line_count": 50}],
            "file_tree": ["src/main.rs", "Cargo.toml"],
            "doc_analyses": [{"subtopic": "Overview", "summary": "Core CLI"}],
            "confidence_score": 1.0,
            "needs_review": False,
        },
    )

    result = await writer.run(task)
    assert result.success is True
    assert result.output["needs_review"] is True
    sec = result.output["sections"][0]
    # Sentence must NOT have fake_crypto_layer.rs deleted to create broken grammar
    assert "fake_crypto_layer.rs" in sec["content"]
    # Must have a prominent visible verification notice attached
    assert "Verification Notice (Needs Review)" in sec["content"]


@pytest.mark.asyncio
async def test_writer_academic_query_regression_with_real_dois():
    """Verify free-text research query mode continues producing peer-reviewed academic DOI citations without regression."""
    from src.agents.writer import WriterAgent
    from unittest.mock import AsyncMock

    provider = AsyncMock()
    # LLM completion error triggers grounded academic fallback
    provider.complete = AsyncMock(side_effect=RuntimeError("Test fallback"))
    writer = WriterAgent(provider=provider)

    research_outputs = [
        {
            "subtopic": "Consensus Protocols",
            "summary": "Byzantine fault tolerance relies on deterministic quorum slices.",
            "claims": [
                {
                    "claim_text": "Stellar consensus protocol guarantees safety under open membership.",
                    "source_url": "https://doi.org/10.1145/3342195.3387531",
                },
                {
                    "claim_text": "PBFT achieves consensus with 3f+1 nodes under partial synchrony.",
                    "source_url": "https://doi.org/10.1145/571637.571640",
                },
            ],
        }
    ]

    task = AgentTask(
        task_type="write_report",
        payload={
            "query": "Byzantine fault tolerance in distributed ledgers",
            "source_type": "query",
            "research_outputs": research_outputs,
        },
    )

    result = await writer.run(task)
    assert result.success is True
    sections = result.output["sections"]
    assert len(sections) >= 3

    # Academic mode must retain real DOIs
    dois = [c for s in sections for c in s.get("citations", []) if "doi.org" in c]
    assert len(dois) >= 2
    assert "https://doi.org/10.1145/3342195.3387531" in dois
    assert "https://doi.org/10.1145/571637.571640" in dois

