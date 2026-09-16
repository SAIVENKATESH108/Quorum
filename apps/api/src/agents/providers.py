import asyncio
import enum
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Callable, List, Optional

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Base exception for AI provider errors."""
    pass


class ProviderUnavailableError(ProviderError):
    """Raised when a provider is unavailable (e.g. circuit breaker is open or retries exhausted)."""
    pass


class CircuitBreakerOpenError(ProviderUnavailableError):
    """Raised specifically when the circuit breaker is in the OPEN state."""
    pass


class CircuitBreakerState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker pattern implementation:
    - CLOSED: normal operations; records consecutive failures.
    - OPEN: trips after failure_threshold (default 3); rejects requests immediately for cooldown_seconds (default 60s).
    - HALF_OPEN: after cooldown, allows a single trial call. Success closes the breaker; failure re-opens it.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 60.0,
        time_func: Callable[[], float] = time.monotonic,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._time_func = time_func

        self.state = CircuitBreakerState.CLOSED
        self.consecutive_failures = 0
        self.opened_at: Optional[float] = None
        self._lock = asyncio.Lock()

    async def check_or_raise(self, provider_name: str) -> None:
        """Inspect state and determine whether a call is permitted."""
        async with self._lock:
            now = self._time_func()
            if self.state == CircuitBreakerState.OPEN:
                if self.opened_at is not None and (now - self.opened_at) >= self.cooldown_seconds:
                    logger.info(
                        f"Circuit breaker for '{provider_name}' transitioned from OPEN to HALF_OPEN (cooldown expired)."
                    )
                    self.state = CircuitBreakerState.HALF_OPEN
                else:
                    remaining = (
                        self.cooldown_seconds - (now - (self.opened_at or now))
                        if self.opened_at
                        else self.cooldown_seconds
                    )
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker for provider '{provider_name}' is OPEN. Retry in {max(0.0, remaining):.1f}s."
                    )

    async def record_success(self, provider_name: str) -> None:
        """Record a successful execution."""
        async with self._lock:
            if self.state in (CircuitBreakerState.HALF_OPEN, CircuitBreakerState.OPEN):
                logger.info(
                    f"Circuit breaker for '{provider_name}' recovered to CLOSED after successful call."
                )
            self.state = CircuitBreakerState.CLOSED
            self.consecutive_failures = 0
            self.opened_at = None

    async def record_failure(self, provider_name: str) -> None:
        """Record a failed execution."""
        async with self._lock:
            self.consecutive_failures += 1
            now = self._time_func()
            if self.state == CircuitBreakerState.HALF_OPEN:
                logger.warning(
                    f"Trial call in HALF_OPEN failed for '{provider_name}'. Returning to OPEN for {self.cooldown_seconds}s."
                )
                self.state = CircuitBreakerState.OPEN
                self.opened_at = now
            elif self.consecutive_failures >= self.failure_threshold:
                logger.warning(
                    f"Provider '{provider_name}' reached {self.consecutive_failures} consecutive failures. Opening circuit breaker."
                )
                self.state = CircuitBreakerState.OPEN
                self.opened_at = now


class AIProvider(ABC):
    """Abstract Strategy interface for LLM completions."""

    name: str

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 60.0,
        max_retries: int = 3,
        base_delay: float = 0.5,
        time_func: Callable[[], float] = time.monotonic,
    ):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            cooldown_seconds=cooldown_seconds,
            time_func=time_func,
        )
        self.max_retries = max_retries
        self.base_delay = base_delay

    @abstractmethod
    async def _call_api(self, prompt: str, system: Optional[str] = None) -> str:
        """Execute raw API call to LLM provider."""
        pass

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Execute completion wrapped in circuit breaker and exponential backoff retry.
        Does NOT retry if circuit breaker is open.
        """
        await self.circuit_breaker.check_or_raise(self.name)

        last_exception: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self._call_api(prompt, system=system)
                await self.circuit_breaker.record_success(self.name)
                return response
            except ProviderUnavailableError:
                # Do not retry on circuit breaker open
                raise
            except Exception as exc:
                last_exception = exc
                is_transient = self._is_transient_error(exc)
                logger.warning(
                    f"[{self.name}] Attempt {attempt}/{self.max_retries} failed: {exc} (transient={is_transient})"
                )

                if attempt < self.max_retries and is_transient:
                    # Exponential backoff with jitter
                    delay = (self.base_delay * (2 ** (attempt - 1))) + random.uniform(0.05, 0.15)
                    await asyncio.sleep(delay)
                else:
                    # All retries exhausted or non-transient error
                    break

        # Record failure in circuit breaker
        await self.circuit_breaker.record_failure(self.name)
        raise ProviderUnavailableError(
            f"Provider '{self.name}' failed after {self.max_retries} attempts: {last_exception}"
        ) from last_exception

    def _is_transient_error(self, exc: Exception) -> bool:
        """Determine whether an error is transient (network timeout, 5xx server error)."""
        if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError)):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code >= 500 or exc.response.status_code == 429
        return True


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider."""

    name = "Anthropic"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_key = api_key or settings.ANTHROPIC_API_KEY or ""
        self.model = model

    async def _call_api(self, prompt: str, system: Optional[str] = None) -> str:
        if not self.api_key or self.api_key.startswith("test_") or self.api_key.startswith("your_"):
            # Mock / stub response when test key is configured
            return f"[Anthropic Mock Response - {self.model}]\nResearch Analysis:\n{prompt[:300]}..."

        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            body = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                body["system"] = system

            res = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
            res.raise_for_status()
            data = res.json()
            return data["content"][0]["text"]


class OpenAIProvider(AIProvider):
    """OpenAI GPT API provider."""

    name = "OpenAI"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_key = api_key or settings.OPENAI_API_KEY or ""
        self.model = model

    async def _call_api(self, prompt: str, system: Optional[str] = None) -> str:
        if not self.api_key or self.api_key.startswith("test_") or self.api_key.startswith("your_"):
            # Mock / stub response when test key is configured
            return f"[OpenAI Mock Response - {self.model}]\nExecutive Synthesis:\n{prompt[:300]}..."

        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            body = {
                "model": self.model,
                "messages": messages,
            }
            res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body)
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"]


class NeuralPulseProvider(AIProvider):
    """
    Evorozen Neural Pulse API provider.
    Neural Pulse is Evorozen's cognitive state and virtual memory platform for autonomous agents.
    NOTE: Evorozen distributes API credentials and documentation via official community Discord channels.
    """

    name = "NeuralPulse"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.evorozen.com/v1/neural-pulse",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_key = api_key or settings.NEURAL_PULSE_API_KEY or ""
        self.base_url = base_url

    async def _call_api(self, prompt: str, system: Optional[str] = None) -> str:
        # TODO: Evorozen Neural Pulse endpoint integration. Update with team workspace endpoints once registered.
        if not self.api_key or self.api_key.startswith("test_") or self.api_key.startswith("your_"):
            return f"[NeuralPulse Cognitive Memory Response]\nConsensus Claims Analysis:\n{prompt[:300]}..."

        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "prompt": prompt,
                "system_instruction": system,
                "context_type": "research_synthesis",
            }
            res = await client.post(f"{self.base_url}/complete", headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
            return data.get("text") or data.get("completion") or str(data)


class ProviderFallbackChain(AIProvider):
    """
    Fallback chain that tries providers in configured priority order.
    Falls through to the next provider on ProviderUnavailableError.
    """

    name = "FallbackChain"

    def __init__(self, providers: List[AIProvider]):
        super().__init__()
        self.providers = providers

    async def _call_api(self, prompt: str, system: Optional[str] = None) -> str:
        # ProviderFallbackChain overrides complete() directly
        return await self.complete(prompt, system=system)

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        """Attempt completion through providers in priority sequence."""
        if not self.providers:
            raise ProviderUnavailableError("No providers configured in fallback chain.")

        errors: List[str] = []
        for provider in self.providers:
            try:
                logger.debug(f"[FallbackChain] Attempting provider '{provider.name}'...")
                return await provider.complete(prompt, system=system)
            except ProviderUnavailableError as exc:
                logger.warning(f"[FallbackChain] Provider '{provider.name}' unavailable: {exc}. Falling through...")
                errors.append(f"{provider.name}: {exc}")
                continue
            except Exception as exc:
                logger.warning(f"[FallbackChain] Unexpected error with '{provider.name}': {exc}. Falling through...")
                errors.append(f"{provider.name}: {exc}")
                continue

        raise ProviderUnavailableError(
            f"All providers in fallback chain failed. Failures: {'; '.join(errors)}"
        )


def get_default_provider() -> AIProvider:
    """Instantiate standard provider fallback chain based on configuration."""
    from src.agents.providers import AnthropicProvider, NeuralPulseProvider, OpenAIProvider

    providers: List[AIProvider] = [
        AnthropicProvider(),
        OpenAIProvider(),
        NeuralPulseProvider(),
    ]
    return ProviderFallbackChain(providers)

