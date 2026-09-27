import uuid
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from src.agents.providers import (
    AIProvider,
    CircuitBreakerState,
    NeuralPulseProvider,
    NeuralPulseError,
    NeuralPulseAuthError,
    NeuralPulsePromptTooLargeError,
    NeuralPulseQuotaExceeded,
    ProviderError,
    ProviderUnavailableError,
    ProviderFallbackChain,
    get_default_provider,
    record_provider_observation,
    get_provider_observation,
    reset_provider_observations,
)
from src.main import app
from src.db.models import User, UserRole
from src.core.security import get_current_user

test_member = User(
    id=uuid.uuid4(),
    email="test_member@example.com",
    name="Test Member",
    role=UserRole.MEMBER.value,
)

test_guest = User(
    id=uuid.uuid4(),
    email="test_guest@example.com",
    name="Guest Judge",
    role=UserRole.GUEST.value,
)


# ── Test 1: Endpoint path, POST method, and Authorization header construction ─
@pytest.mark.asyncio
async def test_01_endpoint_path_method_headers():
    provider = NeuralPulseProvider(api_key="mock_key_secret_123", base_url="https://pulse.evorozen.com/api/neural")
    mock_post = AsyncMock()
    mock_post.return_value = httpx.Response(200, json={"response": "Valid response text", "traceId": "trace-001"})

    with patch("httpx.AsyncClient.post", mock_post):
        res = await provider.complete("Test prompt")
        assert res == "Valid response text"

    mock_post.assert_called_once()
    called_url = mock_post.call_args[0][0]
    called_headers = mock_post.call_args[1]["headers"]

    assert called_url == "https://pulse.evorozen.com/api/neural"
    assert called_headers["Authorization"] == "Bearer mock_key_secret_123"
    assert called_headers["Content-Type"] == "application/json"


# ── Test 2: Correct action_type=chat payload ─────────────────────────────────
@pytest.mark.asyncio
async def test_02_correct_action_type_chat_payload():
    provider = NeuralPulseProvider(api_key="mock_key_xyz")
    mock_post = AsyncMock(return_value=httpx.Response(200, json={"response": "OK response"}))

    with patch("httpx.AsyncClient.post", mock_post):
        await provider.complete("Analyze consensus invariants")

    called_payload = mock_post.call_args[1]["json"]
    assert called_payload["action_type"] == "chat"
    assert called_payload["prompt"] == "Analyze consensus invariants"


# ── Test 3: No unsupported parameters sent ───────────────────────────────────
@pytest.mark.asyncio
async def test_03_no_unsupported_parameters_sent():
    provider = NeuralPulseProvider(api_key="mock_key_xyz")
    mock_post = AsyncMock(return_value=httpx.Response(200, json={"response": "OK"}))

    with patch("httpx.AsyncClient.post", mock_post):
        await provider.complete("Query with system", system="System instruction")

    called_payload = mock_post.call_args[1]["json"]
    # Documented fields only: action_type and prompt
    assert set(called_payload.keys()) == {"action_type", "prompt"}
    assert "model" not in called_payload
    assert "temperature" not in called_payload
    assert "max_tokens" not in called_payload
    assert "system" not in called_payload


# ── Test 4: Correct parsing of response field ────────────────────────────────
@pytest.mark.asyncio
async def test_04_parsing_of_response_field():
    provider = NeuralPulseProvider(api_key="mock_key_xyz")
    mock_post = AsyncMock(return_value=httpx.Response(
        200,
        json={"response": "Verified multi-agent consensus reached.", "traceId": "trace-abc-123"}
    ))

    with patch("httpx.AsyncClient.post", mock_post):
        output = await provider.complete("Evaluate consensus")
        assert output == "Verified multi-agent consensus reached."


# ── Test 5: Compatibility parsing of text field ──────────────────────────────
@pytest.mark.asyncio
async def test_05_compatibility_parsing_of_text_field():
    provider = NeuralPulseProvider(api_key="mock_key_xyz")
    mock_post = AsyncMock(return_value=httpx.Response(
        200,
        json={"text": "Fallback text format parsed successfully.", "traceId": "trace-def-456"}
    ))

    with patch("httpx.AsyncClient.post", mock_post):
        output = await provider.complete("Evaluate text format")
        assert output == "Fallback text format parsed successfully."


# ── Test 6: Missing response and text raises controlled ProviderError ─────────
@pytest.mark.asyncio
async def test_06_missing_response_and_text_raises_provider_error():
    provider = NeuralPulseProvider(api_key="mock_key_xyz")
    mock_post = AsyncMock(return_value=httpx.Response(
        200,
        json={"traceId": "trace-empty", "status": "ok"}
    ))

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(ProviderError) as exc_info:
            await provider.complete("Evaluate empty")
        assert "empty or invalid response" in str(exc_info.value)


# ── Test 7: 401 produces safe NeuralPulseAuthError without leaking key ────────
@pytest.mark.asyncio
async def test_07_auth_error_no_key_leak():
    secret_key = "super_secret_token_123"
    provider = NeuralPulseProvider(api_key=secret_key)
    mock_post = AsyncMock(return_value=httpx.Response(401, json={"error": "Unauthorized. API Key is missing or invalid format."}))

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(NeuralPulseAuthError) as exc_info:
            await provider.complete("Evaluate auth")

        err_text = str(exc_info.value)
        assert secret_key not in err_text
        assert "authentication failed" in err_text.lower()


# ── Test 8: 429 LLM_LIMIT_EXCEEDED raises typed NeuralPulseQuotaExceeded ─────
@pytest.mark.asyncio
async def test_08_quota_exceeded_error_fields():
    provider = NeuralPulseProvider(api_key="mock_key_xyz")
    mock_post = AsyncMock(return_value=httpx.Response(
        429,
        json={
            "error": "LLM call limit reached. Your Free plan allows 25 AI calls/month.",
            "code": "LLM_LIMIT_EXCEEDED",
            "plan": "Free",
            "llm_limit": 25,
            "llm_used": 26,
            "traceId": "trace-429-xyz"
        }
    ))

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(NeuralPulseQuotaExceeded) as exc_info:
            await provider.complete("Evaluate quota")

        err = exc_info.value
        assert err.status_code == 429
        assert err.code == "LLM_LIMIT_EXCEEDED"
        assert err.provider_name == "NeuralPulse"
        assert "quota is currently exhausted" in str(err)


# ── Test 9: 429 does not trigger immediate retry storm ───────────────────────
@pytest.mark.asyncio
async def test_09_quota_exceeded_no_retry_storm():
    provider = NeuralPulseProvider(api_key="mock_key_xyz", max_retries=3)
    mock_post = AsyncMock(return_value=httpx.Response(
        429,
        json={"error": "LLM call limit reached.", "code": "LLM_LIMIT_EXCEEDED"}
    ))

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(NeuralPulseQuotaExceeded):
            await provider.complete("Evaluate retries")

    # Critical: called exactly ONCE, 0 retries
    assert mock_post.call_count == 1


# ── Test 10: 500/502 produces ProviderUnavailableError ───────────────────────
@pytest.mark.asyncio
async def test_10_500_502_provider_unavailable():
    provider = NeuralPulseProvider(api_key="mock_key_xyz")
    mock_post = AsyncMock(return_value=httpx.Response(502, text="Bad Gateway"))

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await provider.complete("Evaluate 502")
        assert "status 502" in str(exc_info.value)


# ── Test 11: Timeout and network error handling ──────────────────────────────
@pytest.mark.asyncio
async def test_11_timeout_and_network_error():
    provider = NeuralPulseProvider(api_key="mock_key_xyz")
    mock_post = AsyncMock(side_effect=httpx.TimeoutException("Read timed out"))

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await provider.complete("Evaluate timeout")
        assert "timed out" in str(exc_info.value).lower()


# ── Test 12: Circuit breaker integration ─────────────────────────────────────
@pytest.mark.asyncio
async def test_12_circuit_breaker_trips():
    provider = NeuralPulseProvider(api_key="mock_key_xyz", failure_threshold=2, cooldown_seconds=60.0, max_retries=1)
    mock_post = AsyncMock(return_value=httpx.Response(500, text="Internal Server Error"))

    with patch("httpx.AsyncClient.post", mock_post):
        # First failure
        with pytest.raises(ProviderUnavailableError):
            await provider.complete("Call 1")
        assert provider.circuit_breaker.state == CircuitBreakerState.CLOSED

        # Second failure -> trips breaker
        with pytest.raises(ProviderUnavailableError):
            await provider.complete("Call 2")
        assert provider.circuit_breaker.state == CircuitBreakerState.OPEN


# ── Test 13: API key never appears in error strings or logs ──────────────────
@pytest.mark.asyncio
async def test_13_api_key_masked_in_all_errors():
    canary_key = "CANARY_KEY_NEVER_LEAK_THIS_STRING"
    provider = NeuralPulseProvider(api_key=canary_key)
    mock_post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(Exception) as exc_info:
            await provider.complete("Canary test")
        assert canary_key not in repr(exc_info.value)
        assert canary_key not in str(exc_info.value)


# ── Test 14: Explicit neural_pulse selection does not silently fall back ─────
@pytest.mark.asyncio
async def test_14_explicit_neural_pulse_never_silently_falls_back():
    provider = get_default_provider("neural_pulse")
    assert isinstance(provider, NeuralPulseProvider)
    # Never wrapped in ProviderFallbackChain
    assert not isinstance(provider, ProviderFallbackChain)

    mock_post = AsyncMock(return_value=httpx.Response(429, json={"code": "LLM_LIMIT_EXCEEDED"}))
    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(NeuralPulseQuotaExceeded):
            await provider.complete("Explicit mode test")


# ── Test 15: Cloud fallback chain preserves sequence without Neural Pulse ─────
@pytest.mark.asyncio
async def test_15_cloud_fallback_chain_excludes_neural_pulse():
    chain = get_default_provider("cloud")
    assert isinstance(chain, ProviderFallbackChain)
    provider_names = [p.name for p in chain.providers]

    assert "NeuralPulse" not in provider_names
    assert provider_names == ["OpenRouter", "Gemini", "OpenAI"]


# ── Test 16: Prompt exceeding 2,000 characters triggers input-limit error ────
@pytest.mark.asyncio
async def test_16_prompt_exceeding_2000_chars_raises_error():
    provider = NeuralPulseProvider(api_key="mock_key_xyz")
    mock_post = AsyncMock()

    long_prompt = "A" * 2001
    with patch("httpx.AsyncClient.post", mock_post):
        with pytest.raises(NeuralPulsePromptTooLargeError) as exc_info:
            await provider.complete(long_prompt)
        assert "exceeds Neural Pulse's supported prompt size" in str(exc_info.value)

    # Asserts request was blocked BEFORE outbound dispatch
    mock_post.assert_not_called()


# ── Test 17: Cloud mode never invokes NeuralPulseProvider ────────────────────
@pytest.mark.asyncio
async def test_17_cloud_mode_never_invokes_neural_pulse():
    chain = get_default_provider("cloud")
    mock_np = AsyncMock()

    with patch.object(NeuralPulseProvider, "_call_api", mock_np):
        with patch("src.agents.providers.OpenRouterProvider._call_api", return_value="OpenRouter output"):
            res = await chain.complete("Test cloud invocation")
            assert res == "OpenRouter output"

    mock_np.assert_not_called()


# ── Test 18: Explicit neural_pulse mode never invokes cloud/local providers ──
@pytest.mark.asyncio
async def test_18_explicit_neural_pulse_never_invokes_other_providers():
    provider = get_default_provider("neural_pulse")
    mock_or = AsyncMock()
    mock_gemini = AsyncMock()
    mock_ollama = AsyncMock()

    mock_np = AsyncMock(return_value="Neural Pulse output")
    with patch.object(NeuralPulseProvider, "_call_api", mock_np), \
         patch("src.agents.providers.OpenRouterProvider._call_api", mock_or), \
         patch("src.agents.providers.GeminiProvider._call_api", mock_gemini), \
         patch("src.agents.providers.OllamaProvider._call_api", mock_ollama):
        res = await provider.complete("Test direct invocation")
        assert res == "Neural Pulse output"

    mock_or.assert_not_called()
    mock_gemini.assert_not_called()
    mock_ollama.assert_not_called()


# ── Test 19: Provider status endpoint performs zero outbound requests ─────────
def test_19_provider_status_endpoint_zero_outbound_requests():
    reset_provider_observations()
    app.dependency_overrides[get_current_user] = lambda: test_member
    try:
        client = TestClient(app)
        with patch.object(NeuralPulseProvider, "_call_api") as mock_np_api, \
             patch("httpx.AsyncClient.post") as mock_async_post, \
             patch("httpx.AsyncClient.get") as mock_async_get:
            res = client.get("/api/reports/providers/status")
            assert res.status_code == 200

        mock_np_api.assert_not_called()
        mock_async_post.assert_not_called()
        mock_async_get.assert_not_called()
    finally:
        app.dependency_overrides.clear()


# ── Test 20: Provider status returns unknown when configured without history ──
def test_20_provider_status_returns_unknown_when_configured():
    reset_provider_observations()
    app.dependency_overrides[get_current_user] = lambda: test_member
    try:
        client = TestClient(app)
        with patch("src.core.config.settings.NEURAL_PULSE_API_KEY", "configured_dummy_key"):
            res = client.get("/api/reports/providers/status")
            assert res.status_code == 200
            data = res.json()
            assert data["neural_pulse"]["status"] == "unknown"
    finally:
        app.dependency_overrides.clear()


# ── Test 21: Provider status returns quota_exhausted only from cached state ──
def test_21_provider_status_returns_quota_exhausted_from_observation():
    reset_provider_observations()
    record_provider_observation("NeuralPulse", "quota_exhausted")
    app.dependency_overrides[get_current_user] = lambda: test_member
    try:
        client = TestClient(app)
        with patch("src.core.config.settings.NEURAL_PULSE_API_KEY", "configured_dummy_key"):
            res = client.get("/api/reports/providers/status")
            assert res.status_code == 200
            data = res.json()
            assert data["neural_pulse"]["status"] == "quota_exhausted"
            assert data["neural_pulse"]["observed_at"] is not None
    finally:
        app.dependency_overrides.clear()


# ── Test 22: Guest cannot create report using neural_pulse mode ──────────────
def test_22_guest_cannot_create_report_neural_pulse():
    app.dependency_overrides[get_current_user] = lambda: test_guest
    try:
        client = TestClient(app)
        dummy_project_id = str(uuid.uuid4())
        res = client.post(
            f"/api/projects/{dummy_project_id}/reports",
            json={"query": "Research quantum states", "provider_mode": "neural_pulse"}
        )
        # Guest Judge mutating request must be 403 Forbidden
        assert res.status_code == 403
    finally:
        app.dependency_overrides.clear()


# ── Test 23: Anonymous user cannot access provider status endpoint ────────────
def test_23_anonymous_cannot_access_provider_status():
    app.dependency_overrides.clear()
    client = TestClient(app)
    res = client.get("/api/reports/providers/status")
    # Anonymous request must be 401 Unauthorized
    assert res.status_code == 401


# ── Test 24: Provider status response contains zero leaked internals ─────────
def test_24_provider_status_response_contains_zero_leaks():
    reset_provider_observations()
    record_provider_observation("NeuralPulse", "quota_exhausted")
    app.dependency_overrides[get_current_user] = lambda: test_member
    try:
        client = TestClient(app)
        with patch("src.core.config.settings.NEURAL_PULSE_API_KEY", "SECRET_KEY_NEVER_REVEAL"):
            res = client.get("/api/reports/providers/status")
            assert res.status_code == 200
            raw_text = res.text

        assert "SECRET_KEY_NEVER_REVEAL" not in raw_text
        assert "Bearer" not in raw_text
        assert "plan" not in raw_text
        assert "limit" not in raw_text
        assert "usage" not in raw_text
        assert "traceId" not in raw_text
        assert "trace_id" not in raw_text
        assert "pulse.evorozen.com" not in raw_text
    finally:
        app.dependency_overrides.clear()
