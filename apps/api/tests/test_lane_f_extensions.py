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
            assert node["payload"]["key_files"][0]["path"] == "README.md"
