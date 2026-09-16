import asyncio
import pytest
from typing import Optional

from src.agents.providers import (
    AIProvider,
    CircuitBreaker,
    CircuitBreakerState,
    ProviderFallbackChain,
    ProviderUnavailableError,
)


class MockTime:
    def __init__(self, initial_time: float = 1000.0):
        self.current_time = initial_time

    def time(self) -> float:
        return self.current_time

    def advance(self, seconds: float) -> None:
        self.current_time += seconds


class ControllableProvider(AIProvider):
    name = "Controllable"

    def __init__(self, mock_time: MockTime, **kwargs):
        super().__init__(
            failure_threshold=3,
            cooldown_seconds=60.0,
            time_func=mock_time.time,
            base_delay=0.01,
            **kwargs,
        )
        self.mock_time = mock_time
        self.fail_calls = False
        self.call_count = 0

    async def _call_api(self, prompt: str, system: Optional[str] = None) -> str:
        self.call_count += 1
        if self.fail_calls:
            raise RuntimeError("Simulated API failure")
        return f"Response to: {prompt}"


@pytest.mark.asyncio
async def test_circuit_breaker_transitions():
    """Test full cycle: CLOSED -> OPEN after 3 failures -> HALF_OPEN after cooldown -> CLOSED on success."""
    clock = MockTime()
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0, time_func=clock.time)

    assert cb.state == CircuitBreakerState.CLOSED

    # Failures 1 & 2: Still CLOSED
    await cb.record_failure("TestProvider")
    assert cb.state == CircuitBreakerState.CLOSED
    await cb.record_failure("TestProvider")
    assert cb.state == CircuitBreakerState.CLOSED

    # Failure 3: Trips to OPEN
    await cb.record_failure("TestProvider")
    assert cb.state == CircuitBreakerState.OPEN

    # While OPEN during cooldown, calls are rejected immediately
    with pytest.raises(ProviderUnavailableError) as excinfo:
        await cb.check_or_raise("TestProvider")
    assert "is OPEN" in str(excinfo.value)

    # Advance time 59s: Still OPEN
    clock.advance(59.0)
    with pytest.raises(ProviderUnavailableError):
        await cb.check_or_raise("TestProvider")

    # Advance time 2s (total 61s > 60s cooldown): Transitions to HALF_OPEN
    clock.advance(2.0)
    await cb.check_or_raise("TestProvider")
    assert cb.state == CircuitBreakerState.HALF_OPEN

    # Success in HALF_OPEN resets breaker to CLOSED
    await cb.record_success("TestProvider")
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.consecutive_failures == 0


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure_reopens():
    """Test that a failure during trial call in HALF_OPEN re-opens the breaker."""
    clock = MockTime()
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0, time_func=clock.time)

    # Trip to OPEN
    for _ in range(3):
        await cb.record_failure("TestProvider")
    assert cb.state == CircuitBreakerState.OPEN

    # Cooldown expires -> HALF_OPEN
    clock.advance(60.1)
    await cb.check_or_raise("TestProvider")
    assert cb.state == CircuitBreakerState.HALF_OPEN

    # Trial call fails -> returns to OPEN
    await cb.record_failure("TestProvider")
    assert cb.state == CircuitBreakerState.OPEN

    # Immediate check raises ProviderUnavailableError
    with pytest.raises(ProviderUnavailableError):
        await cb.check_or_raise("TestProvider")


@pytest.mark.asyncio
async def test_provider_exponential_backoff():
    """Test that transient failures trigger retries with backoff."""
    clock = MockTime()
    provider = ControllableProvider(clock, max_retries=3)

    # Make it fail 2 times then succeed
    attempts = 0

    async def flaky_call(prompt: str, system: Optional[str] = None) -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("Transient 503 Server Error")
        return "Recovered Success"

    provider._call_api = flaky_call

    result = await provider.complete("Test Prompt")
    assert result == "Recovered Success"
    assert attempts == 3
    assert provider.circuit_breaker.state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_provider_fallback_chain():
    """Test that FallbackChain falls through to secondary provider when primary fails."""
    clock = MockTime()

    # Primary provider configured to fail and trip breaker
    primary = ControllableProvider(clock, max_retries=1)
    primary.name = "PrimaryProvider"
    primary.fail_calls = True

    # Secondary provider configured to succeed
    secondary = ControllableProvider(clock)
    secondary.name = "SecondaryProvider"
    secondary.fail_calls = False

    chain = ProviderFallbackChain(providers=[primary, secondary])

    result = await chain.complete("Evaluate Consensus")
    assert result == "Response to: Evaluate Consensus"
    assert secondary.call_count == 1
    assert primary.circuit_breaker.consecutive_failures >= 1
