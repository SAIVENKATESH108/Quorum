import asyncio
import enum
import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Callable

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Base exception for AI provider errors."""


class ProviderUnavailableError(ProviderError):
    """Raised when a provider is unavailable (e.g. circuit breaker is open or retries exhausted)."""


class CircuitBreakerOpenError(ProviderUnavailableError):
    """Raised specifically when the circuit breaker is in the OPEN state."""


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
        self.opened_at: float | None = None
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
    async def _call_api(self, prompt: str, system: str | None = None) -> str:
        """Execute raw API call to LLM provider."""

    async def complete(self, prompt: str, system: str | None = None) -> str:
        """
        Execute completion wrapped in circuit breaker and exponential backoff retry.
        Does NOT retry if circuit breaker is open.
        """
        await self.circuit_breaker.check_or_raise(self.name)

        last_exception: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self._call_api(prompt, system=system)
                await self.circuit_breaker.record_success(self.name)
                return response
            except ProviderUnavailableError:
                # Do not retry on circuit breaker open
                raise
            except Exception as exc:  # noqa: BLE001
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
        api_key: str | None = None,
        model: str = "claude-3-5-sonnet-20241022",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_key = api_key or settings.ANTHROPIC_API_KEY or ""
        self.model = model

    async def _call_api(self, prompt: str, system: str | None = None) -> str:
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
        api_key: str | None = None,
        model: str = "gpt-4o",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_key = api_key or settings.OPENAI_API_KEY or ""
        self.model = model

    async def _call_api(self, prompt: str, system: str | None = None) -> str:
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


class OpenRouterProvider(AIProvider):
    """
    OpenRouter API provider - aggregates 100+ free and paid LLM models.
    Uses OpenAI-compatible chat completions endpoint.
    Default model: nvidia/nemotron-3-ultra-550b-a55b:free (free tier, 1M context).
    """

    name = "OpenRouter"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "nvidia/nemotron-3-ultra-550b-a55b:free",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_key = api_key or settings.OPENROUTER_API_KEY or ""
        self.model = model

    async def _call_api(self, prompt: str, system: str | None = None) -> str:
        if not self.api_key or self.api_key.startswith("test_") or self.api_key.startswith("your_"):
            return f"[OpenRouter Mock Response - {self.model}]\nResearch Analysis:\n{prompt[:300]}..."

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://quorum.ai",
                "X-Title": "Quorum Research Platform",
            }
            body = {
                "model": self.model,
                "messages": messages,
            }
            res = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=body,
            )
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"]


class GeminiProvider(AIProvider):
    """
    Google Gemini API provider via REST (google-generativeai compatible endpoint).
    Uses the Gemini 1.5 Flash model by default — fast, capable, and generous free tier.
    """

    name = "Gemini"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-1.5-flash",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_key = api_key or settings.GEMINI_API_KEY or ""
        self.model = model

    async def _call_api(self, prompt: str, system: str | None = None) -> str:
        if not self.api_key or self.api_key.startswith("test_") or self.api_key.startswith("your_"):
            return f"[Gemini Mock Response - {self.model}]\nResearch Analysis:\n{prompt[:300]}..."

        # Build contents list (Gemini uses 'contents' not 'messages')
        contents = []
        if system:
            # Gemini 1.5 supports system_instruction via the dedicated field
            pass  # handled below
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        body: dict = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": 8192,
                "temperature": 0.7,
            },
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}"
            f":generateContent?key={self.api_key}"
        )
        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(url, json=body)
            res.raise_for_status()
            data = res.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as exc:
                raise ValueError(f"Unexpected Gemini response format: {data}") from exc


class NeuralPulseProvider(AIProvider):
    """
    Evorozen Neural Pulse API provider.
    Neural Pulse is Evorozen's cognitive state and virtual memory platform for autonomous agents.
    NOTE: Evorozen distributes API credentials and documentation via official community Discord channels.
    """

    name = "NeuralPulse"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.evorozen.com/v1/neural-pulse",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_key = api_key or settings.NEURAL_PULSE_API_KEY or ""
        self.base_url = base_url

    async def _call_api(self, prompt: str, system: str | None = None) -> str:
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


class OllamaProvider(AIProvider):
    """
    Local Ollama API provider for offline/air-gapped multi-agent research.
    Connects to local Ollama runtime (default: http://localhost:11434).
    Supports local models such as llama3, mistral, qwen2.5, phi3, deepseek-r1.
    """

    name = "Ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.base_url = (base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or getattr(settings, "OLLAMA_MODEL", "llama3")
        self.timeout = timeout

    async def is_available(self) -> bool:
        """Pings Ollama tags endpoint to verify if local service is running."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    async def _call_api(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                    },
                )
                res.raise_for_status()
                data = res.json()
                return data.get("message", {}).get("content", "")
            except httpx.ConnectError as exc:
                raise ProviderUnavailableError(
                    f"Ollama local instance not reachable at {self.base_url}. Please run 'ollama serve'."
                ) from exc
            except Exception as exc:
                raise ProviderError(f"Ollama execution error: {exc}") from exc


class ProviderFallbackChain(AIProvider):
    """
    Fallback chain that tries providers in configured priority order.
    Falls through to the next provider on ProviderUnavailableError.
    """

    name = "FallbackChain"

    def __init__(self, providers: list[AIProvider]):
        super().__init__()
        self.providers = providers

    async def _call_api(self, prompt: str, system: str | None = None) -> str:
        # ProviderFallbackChain overrides complete() directly
        return await self.complete(prompt, system=system)

    async def complete(self, prompt: str, system: str | None = None) -> str:
        """Attempt completion through providers in priority sequence."""
        if not self.providers:
            raise ProviderUnavailableError("No providers configured in fallback chain.")

        errors: list[str] = []
        for provider in self.providers:
            try:
                logger.debug(f"[FallbackChain] Attempting provider '{provider.name}'...")
                return await provider.complete(prompt, system=system)
            except ProviderUnavailableError as exc:
                logger.warning(f"[FallbackChain] Provider '{provider.name}' unavailable: {exc}. Falling through...")
                errors.append(f"{provider.name}: {exc}")
                continue
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[FallbackChain] Unexpected error with '{provider.name}': {exc}. Falling through...")
                errors.append(f"{provider.name}: {exc}")
                continue

        raise ProviderUnavailableError(
            f"All providers in fallback chain failed. Failures: {'; '.join(errors)}"
        )


def get_default_provider(mode: str = "cloud") -> AIProvider:
    """
    Instantiate provider fallback chain.
    If mode is 'local' or 'offline', pins strictly to OllamaProvider (zero cloud calls).
    Otherwise Priority: OpenRouter → Gemini → OpenAI → NeuralPulse → Ollama.
    """
    if mode in ("local", "offline"):
        return OllamaProvider()

    providers: list[AIProvider] = [
        OpenRouterProvider(),
        GeminiProvider(),
        OpenAIProvider(),
        NeuralPulseProvider(),
        OllamaProvider(),
    ]
    return ProviderFallbackChain(providers)


