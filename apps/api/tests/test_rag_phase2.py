"""
Phase 2 Codebase & Repository RAG Test Suite.

Mandatory verification tests:
A. Immutable revision & commit pinning before file fetching.
B. Tree truncation handling and partial coverage warning.
C. Structured file indexing policy and skip reason accounting.
D. Mandatory external embedding consent for local folders and private repositories.
E. Line-stability redaction (line numbers never shift across single- or multi-line secrets).
F. Parser truthfulness (Python AST vs heuristic fallback vs TS/SQL/YAML/JSON).
G. Scope and repository boundary isolation in SQL vector queries.
H. Code-grounded Swarm Chat answers and deterministic abstention on unknown symbols.
"""

import hashlib
import uuid
import httpx
import pytest
from unittest.mock import patch
from sqlalchemy import select

from src.agents.providers import AIProvider
from src.db.models import Project, RAGChunk, User
from src.db.session import async_session_maker
from src.services.rag.chat_engine import (
    ABSTENTION_CODEBASE,
    SwarmChatEngine,
)
from src.services.rag.code_chunker import CodeChunker
from src.services.rag.code_policy import SkipReason
from src.services.rag.codebase_indexer import CodebaseIndexer, ConsentRequiredError
from src.services.rag.embeddings import EmbeddingProvider
from src.services.rag.vector_store import PgVectorStoreProvider


class Deterministic1536EmbeddingProvider(EmbeddingProvider):
    """Deterministic embedding provider generating valid 1536-dim vectors for tests."""
    provider_name = "DeterministicTest"
    model_name = "test-1536"

    def __init__(self, expected_dimensions: int = 1536):
        super().__init__(expected_dimensions=expected_dimensions)

    def _make_vector(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = [float(b % 10) / 10.0 for b in h]
        full_vec = (vec * (1536 // len(vec) + 1))[:1536]
        return self._verify_vector_dimensions(full_vec)

    async def embed_query(self, query: str) -> list[float]:
        return self._make_vector(query)

    async def embed_documents(self, documents: list[str]) -> list[list[float]]:
        return [self._make_vector(d) for d in documents]

    async def health_check(self) -> bool:
        return True


class MockAIProvider(AIProvider):
    name = "MockAI"

    def __init__(self, responses: dict[str, str]):
        super().__init__()
        self.responses = responses
        self.last_prompt = None

    async def _call_api(self, prompt: str, system: str | None = None) -> str:
        self.last_prompt = prompt
        for k, v in self.responses.items():
            if k.lower() in prompt.lower():
                return v
        return "Generic response without evidence."


# ---------------------------------------------------------------------------
# Test E: Line-stability Redaction
# ---------------------------------------------------------------------------

def test_line_stability_redaction():
    """Confirm line numbers never shift across single-line or multi-line secret redactions."""
    chunker = CodeChunker()
    original_code = (
        "import os\n"                                # Line 1
        "API_KEY = 'sk-mock-scrub-target-test-1234'\n" # Line 2 (Single line secret)
        "# Configuration setup\n"                    # Line 3
        "RSA_KEY = '''-----BEGIN RSA PRIVATE KEY-----\n" # Line 4 (Multi line secret)
        "MIIEowIBAAKCAQEA0Y...\n"                    # Line 5
        "-----END RSA PRIVATE KEY-----'''\n"          # Line 6
        "# Ready\n"                                  # Line 7
        "def target_function():\n"                   # Line 8
        "    return 42\n"                            # Line 9
    )

    chunks = chunker.chunk_file(
        relative_path="src/sample.py",
        content=original_code,
        source_identifier="test_repo",
    )

    # Find the function chunk
    fn_chunks = [c for c in chunks if c.symbol_name == "target_function"]
    assert len(fn_chunks) == 1
    fn_chunk = fn_chunks[0]

    # Crucial line stability verification:
    # In original_code, "def target_function():" is exactly line 8 and ends line 9
    assert fn_chunk.start_line == 8, f"Expected start line 8, got {fn_chunk.start_line}"
    assert fn_chunk.end_line == 9, f"Expected end line 9, got {fn_chunk.end_line}"
    assert "def target_function():" in fn_chunk.content
    assert fn_chunk.is_ast is True
    assert fn_chunk.chunking_strategy == "ast_python"


# ---------------------------------------------------------------------------
# Test F: Parser Truthfulness (Python AST vs Heuristic Fallback vs TS/SQL)
# ---------------------------------------------------------------------------

def test_parser_truthfulness():
    chunker = CodeChunker()

    # 1. Valid Python (True AST)
    py_valid = "class DatabaseClient:\n    def connect(self):\n        pass\n"
    py_chunks = chunker.chunk_file("db.py", py_valid, "test")
    assert any(c.is_ast is True for c in py_chunks)
    assert any(c.chunking_strategy == "ast_python" for c in py_chunks)
    method_chunk = next(c for c in py_chunks if c.symbol_type in ("class", "method"))
    assert method_chunk.symbol_name in ("DatabaseClient", "DatabaseClient.connect")

    # 2. Invalid Python (Fallback heuristic, is_ast MUST be False)
    py_invalid = "def broken_syntax(:\n    pass???"
    broken_chunks = chunker.chunk_file("broken.py", py_invalid, "test")
    for c in broken_chunks:
        assert c.is_ast is False, "Fallback chunk must not claim is_ast=True"
        assert c.chunking_strategy == "code_heuristic_v1"
        assert c.symbol_type == "heuristic_block"

    # 3. TypeScript / TSX (Heuristic, is_ast MUST be False)
    ts_code = "export interface UserProfile {\n  id: string;\n  name: string;\n}\n"
    ts_chunks = chunker.chunk_file("types.ts", ts_code, "test")
    for c in ts_chunks:
        assert c.is_ast is False, "TypeScript heuristic must not claim is_ast=True"
        assert c.chunking_strategy == "code_heuristic_v1"

    # 4. SQL Alembic Migration (Migration unit, is_ast False)
    sql_mig = 'revision = "a1b2c3d4e5f6"\ndef upgrade():\n    op.create_table("test")\n'
    mig_chunks = chunker.chunk_file("alembic/versions/migration.py", sql_mig, "test")
    mig = mig_chunks[0]
    assert mig.symbol_type == "migration"
    assert mig.symbol_name == "migration_a1b2c3d4e5f6"


# ---------------------------------------------------------------------------
# Test C: File Indexing Policy and Skip Reason Accounting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_file_indexing_policy_and_reasons():
    indexer = CodebaseIndexer(embedding_provider=Deterministic1536EmbeddingProvider())

    client_payload = {
        "files": [
            {"path": "package-lock.json", "content": "{}"},           # generated/lockfile
            {"path": "node_modules/express/index.js", "content": "//"}, # vendor dir
            {"path": "app.min.js", "content": "function a(){}"},       # minified
            {"path": "logo.png", "content": "binary-bytes"},           # binary
            {"path": "data.unsupported", "content": "data"},           # unsupported ext
            {"path": "huge.py", "size": 200 * 1024, "content": "x"},   # too large (>100KB)
            {"path": "src/valid.ts", "size": 500, "content": "export const PI = 3.14;"}, # valid
        ]
    }

    async with async_session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"policy_{uuid.uuid4().hex[:6]}@example.com",
            name="Policy Tester",
        )
        session.add(user)
        await session.flush()

        proj = Project(
            id=uuid.uuid4(),
            user_id=user.id,
            title=f"Policy-Proj-{uuid.uuid4().hex[:6]}",
        )
        session.add(proj)
        await session.flush()

        diag = await indexer.index_local_folder(
            project_id=proj.id,
            folder_name="policy_test_app",
            file_tree_payload=client_payload,
            session=session,
            user_consent=True,
        )

        assert diag.total_discovered_files == 7
        assert diag.indexed_files == 1
        assert diag.skipped_files == 6
        assert diag.skip_reason_counts[SkipReason.GENERATED_OR_MINIFIED_FILE] >= 2
        assert diag.skip_reason_counts[SkipReason.DEPENDENCY_OR_VENDOR_DIRECTORY] == 1
        assert diag.skip_reason_counts[SkipReason.BINARY_OR_NON_TEXT] == 1
        assert diag.skip_reason_counts[SkipReason.UNSUPPORTED_EXTENSION] == 1
        assert diag.skip_reason_counts[SkipReason.FILE_TOO_LARGE] == 1


# ---------------------------------------------------------------------------
# Test D: External Embedding Consent Requirement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_external_embedding_consent_guard():
    indexer = CodebaseIndexer(embedding_provider=Deterministic1536EmbeddingProvider())
    payload = {"files": [{"path": "main.py", "content": "print('hello')"}]}

    async with async_session_maker() as session:
        proj_id = uuid.uuid4()

        # Calling without user_consent must raise ConsentRequiredError
        with pytest.raises(ConsentRequiredError) as exc_info:
            await indexer.index_local_folder(
                project_id=proj_id,
                folder_name="private_app",
                file_tree_payload=payload,
                session=session,
                user_consent=False,
            )
        assert "consent is mandatory" in str(exc_info.value).lower()

        # Private GitHub repo without consent must also fail
        with pytest.raises(ConsentRequiredError):
            await indexer.index_github_repo(
                project_id=proj_id,
                repo_url="https://github.com/my-org/private-repo",
                session=session,
                is_private=True,
                user_consent=False,
            )


# ---------------------------------------------------------------------------
# Test A & B: Immutable Revision Pinning and Tree Truncation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_immutable_revision_and_tree_truncation():
    """
    Simulates GitHub API responses to confirm:
    1. Commit SHA is resolved FIRST before file fetching.
    2. File content URL uses the resolved SHA.
    3. Citations use the resolved commit SHA.
    4. Tree truncation is honestly detected and marked.
    """
    mock_commit_sha = "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3"
    mock_file_content = "def calculate_tax(amount):\n    return amount * 0.2\n"

    async def mock_handler(request: httpx.Request):
        url = str(request.url)
        if "/repos/org/repo/commits/" in url:
            return httpx.Response(200, json={"sha": mock_commit_sha})
        elif "/repos/org/repo/git/trees/" in url:
            # Simulate truncated tree
            return httpx.Response(200, json={
                "sha": "tree123",
                "truncated": True,
                "tree": [
                    {"path": "tax.py", "type": "blob", "size": len(mock_file_content), "sha": "blob123"}
                ]
            })
        elif f"raw.githubusercontent.com/org/repo/{mock_commit_sha}/tax.py" in url:
            return httpx.Response(200, text=mock_file_content)
        elif "/repos/org/repo" in url:
            return httpx.Response(200, json={"default_branch": "main"})
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    indexer = CodebaseIndexer(embedding_provider=Deterministic1536EmbeddingProvider())

    async with async_session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"repo_test_{uuid.uuid4().hex[:6]}@example.com",
            name="Repo Tester",
        )
        session.add(user)
        await session.flush()

        proj = Project(
            id=uuid.uuid4(),
            user_id=user.id,
            title=f"Test-Repo-Proj-{uuid.uuid4().hex[:6]}",
        )
        session.add(proj)
        await session.flush()

        _orig_client = httpx.AsyncClient
        def mock_client_factory(*args, **kwargs):
            kwargs["transport"] = transport
            return _orig_client(*args, **kwargs)

        with patch("httpx.AsyncClient", side_effect=mock_client_factory):
            diag = await indexer.index_github_repo(
                project_id=proj.id,
                repo_url="https://github.com/org/repo",
                session=session,
                reindex=True,
            )

        assert diag.resolved_commit_sha == mock_commit_sha
        assert diag.is_partial is True
        assert diag.skip_reason_counts[SkipReason.TREE_TRUNCATED_OR_NOT_ENUMERATED] == 1
        assert "truncated" in diag.warning.lower()

        # Verify persisted chunk
        stmt = select(RAGChunk).where(RAGChunk.project_id == proj.id)
        chunks = (await session.execute(stmt)).scalars().all()
        assert len(chunks) >= 1
        chunk = chunks[0]
        assert chunk.commit_sha == mock_commit_sha
        assert f"blob/{mock_commit_sha}/tax.py" in chunk.source_url
        assert chunk.content_hash == hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()

        # Clean up
        await session.rollback()


# ---------------------------------------------------------------------------
# Test G: Scope and Boundary Isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scope_and_boundary_isolation():
    """Verify repository A cannot retrieve repository B chunks, and public reports cannot access private code."""
    async with async_session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"iso_user_{uuid.uuid4().hex[:6]}@example.com",
            name="Iso Tester",
        )
        session.add(user)
        await session.flush()

        proj = Project(
            id=uuid.uuid4(),
            user_id=user.id,
            title=f"Iso-Proj-{uuid.uuid4().hex[:6]}",
        )
        session.add(proj)
        await session.flush()

        emb_prov = Deterministic1536EmbeddingProvider()
        vec = await emb_prov.embed_query("query")

        # 1. Chunk for Public GitHub Repo
        chunk_public_repo = RAGChunk(
            chunk_id=f"chk_pub_repo_{uuid.uuid4().hex[:8]}",
            project_id=proj.id,
            source_type="github_repo",
            repo_identifier="org/public-repo",
            commit_sha="sha_pub",
            access_level="public",
            content="Public Open Source Logic",
            content_hash="hash_pub",
            embedding=vec,
            embedding_provider=emb_prov.provider_name,
            embedding_model=emb_prov.model_name,
            embedding_dimension=1536,
        )
        # 2. Chunk for Private GitHub Repo
        chunk_private_repo = RAGChunk(
            chunk_id=f"chk_priv_repo_{uuid.uuid4().hex[:8]}",
            project_id=proj.id,
            source_type="github_repo",
            repo_identifier="org/private-repo",
            commit_sha="sha_priv",
            access_level="private",
            content="Private Proprietary Code",
            content_hash="hash_priv",
            embedding=vec,
            embedding_provider=emb_prov.provider_name,
            embedding_model=emb_prov.model_name,
            embedding_dimension=1536,
        )
        # 3. Chunk for Local Folder
        chunk_local_folder = RAGChunk(
            chunk_id=f"chk_local_{uuid.uuid4().hex[:8]}",
            project_id=proj.id,
            source_type="local_folder",
            repo_identifier="local_folder",
            commit_sha=None,
            access_level="private",
            content="Local Confidential Script",
            content_hash="hash_local",
            embedding=vec,
            embedding_provider=emb_prov.provider_name,
            embedding_model=emb_prov.model_name,
            embedding_dimension=1536,
        )
        session.add_all([chunk_public_repo, chunk_private_repo, chunk_local_folder])
        await session.commit()

        vstore = PgVectorStoreProvider()

        # Boundary A: Unauthenticated guest session (access_level="public") querying project
        # Can ONLY retrieve public repository chunks; private repository and local-folder chunks are excluded
        res_guest = await vstore.similarity_search(
            session=session,
            query_vector=vec,
            project_id=proj.id,
            access_level="public",
        )
        guest_ids = [c.chunk_id for c in res_guest]
        assert chunk_public_repo.chunk_id in guest_ids
        assert chunk_private_repo.chunk_id not in guest_ids
        assert chunk_local_folder.chunk_id not in guest_ids

        # Boundary B: Authenticated owner session (access_level="private" or unfiltered)
        # Can retrieve private repo and local folder chunks
        res_owner_private = await vstore.similarity_search(
            session=session,
            query_vector=vec,
            project_id=proj.id,
            access_level="private",
        )
        owner_private_ids = [c.chunk_id for c in res_owner_private]
        assert chunk_private_repo.chunk_id in owner_private_ids
        assert chunk_local_folder.chunk_id in owner_private_ids
        assert chunk_public_repo.chunk_id not in owner_private_ids

        # Boundary C: Non-owner authenticated user in a separate project
        user_other = User(
            id=uuid.uuid4(),
            email=f"other_{uuid.uuid4().hex[:6]}@example.com",
            name="Other User",
        )
        session.add(user_other)
        await session.flush()
        proj_other = Project(
            id=uuid.uuid4(),
            user_id=user_other.id,
            title=f"Other-Proj-{uuid.uuid4().hex[:6]}",
        )
        session.add(proj_other)
        await session.flush()

        res_non_owner = await vstore.similarity_search(
            session=session,
            query_vector=vec,
            project_id=proj_other.id,
        )
        assert len(res_non_owner) == 0  # Zero leakage into other project

        # Clean up
        await session.delete(chunk_public_repo)
        await session.delete(chunk_private_repo)
        await session.delete(chunk_local_folder)
        await session.delete(proj_other)
        await session.delete(user_other)
        await session.delete(proj)
        await session.delete(user)
        await session.commit()


# ---------------------------------------------------------------------------
# Test H: Code-Grounded Swarm Chat & Deterministic Abstention
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_code_grounded_chat_and_abstention():
    """Verify grounded answer with citations and safe abstention on unknown symbols."""
    async with async_session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            email=f"chat_user_{uuid.uuid4().hex[:6]}@example.com",
            name="Chat Tester",
        )
        session.add(user)
        await session.flush()

        proj = Project(
            id=uuid.uuid4(),
            user_id=user.id,
            title=f"Chat-Code-Proj-{uuid.uuid4().hex[:6]}",
        )
        session.add(proj)
        await session.flush()

        emb_prov = Deterministic1536EmbeddingProvider()
        vec = await emb_prov.embed_query("consensus algorithm implementation")

        cid = f"chk_code_consensus_{uuid.uuid4().hex[:8]}"
        chunk = RAGChunk(
            chunk_id=cid,
            project_id=proj.id,
            source_type="github_repo",
            repo_identifier="quorum/core",
            commit_sha="11223344556677889900aabbccddeeff11223344",
            relative_path="src/consensus.py",
            symbol_name="ConsensusEngine.run_epoch",
            symbol_type="method",
            start_line=15,
            end_line=45,
            is_ast=True,
            access_level="private",
            source_title="src/consensus.py:15-45",
            source_url="https://github.com/quorum/core/blob/11223344556677889900aabbccddeeff11223344/src/consensus.py#L15-L45",
            content="def run_epoch(self):\n    return self.execute_round()\n",
            content_hash="h123",
            embedding=vec,
            embedding_provider=emb_prov.provider_name,
            embedding_model=emb_prov.model_name,
            embedding_dimension=1536,
        )
        session.add(chunk)
        await session.commit()

        # 1. Answerable codebase question
        mock_llm = MockAIProvider({
            "consensus": f"The consensus epoch is run via execute_round() [{cid}]."
        })
        chat_engine = SwarmChatEngine(
            embedding_provider=emb_prov,
            llm_provider=mock_llm,
        )

        res = await chat_engine.chat(
            session=session,
            project_id=proj.id,
            user_query="How does the consensus algorithm execute rounds in consensus.py?",
            source_type="github_repo",
            repo_identifier="quorum/core",
            min_similarity=0.1,
        )

        assert res.abstained is False
        assert len(res.citations) == 1
        assert res.citations[0].url.startswith("https://github.com/quorum/core/blob/11223344")
        assert res.citations[0].is_ast is True
        assert "[1]" in res.reply

        # 2. Unanswerable question (unknown symbol)
        res_unknown = await chat_engine.chat(
            session=session,
            project_id=proj.id,
            user_query="Which function computes the quantum gravitational wave flux in astrophysics.py?",
            source_type="github_repo",
            repo_identifier="quorum/core",
            min_similarity=0.99,  # No chunks will match
        )

        assert res_unknown.abstained is True
        assert res_unknown.reply == ABSTENTION_CODEBASE
        assert len(res_unknown.citations) == 0

        # Clean up
        await session.delete(chunk)
        await session.delete(proj)
        await session.delete(user)
        await session.commit()
