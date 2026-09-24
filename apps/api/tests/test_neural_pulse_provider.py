import pytest
from unittest.mock import patch, MagicMock

from src.agents.providers import (
    NeuralPulseProvider,
    get_default_provider,
    ProviderFallbackChain,
)

def test_neural_pulse_provider_configuration():
    provider = NeuralPulseProvider(api_key="evo_live_sample_key")
    assert provider.name == "NeuralPulse"
    assert provider.base_url == "https://pulse.evorozen.com/api/neural"
    assert provider.circuit_breaker is not None
    assert provider.max_retries == 3

def test_get_default_provider_neural_pulse_mode():
    chain = get_default_provider("neural_pulse")
    assert isinstance(chain, ProviderFallbackChain)
    assert isinstance(chain.providers[0], NeuralPulseProvider)

@pytest.mark.asyncio
async def test_neural_pulse_mock_response():
    provider = NeuralPulseProvider(api_key="test_mock_key")
    resp = await provider.complete("Analyze multi-agent consensus")
    assert "Neural Pulse" in resp
    assert "Analyze multi-agent consensus" in resp

@pytest.mark.asyncio
async def test_neural_pulse_live_schema_response():
    provider = NeuralPulseProvider(api_key="evo_live_sample_key")
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "response": "Synthesized intelligence analysis from Evorozen AI engine.",
        "traceId": "mock-trace-123",
    }

    with patch("httpx.AsyncClient.post", return_value=mock_res):
        resp = await provider.complete("Research quantum networks")
        assert resp == "Synthesized intelligence analysis from Evorozen AI engine."
