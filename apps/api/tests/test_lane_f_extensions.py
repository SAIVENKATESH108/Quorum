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
