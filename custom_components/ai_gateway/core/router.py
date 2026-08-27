"""Weighted failover router for AI Gateway.

Candidates are filtered to enabled, healthy providers that support the
request, then tried in descending weight order. Python's ``sorted`` is
stable, so equal weights fall back to configuration (registration)
order.
"""

from __future__ import annotations

import logging
from typing import Any

from .errors import AllProvidersFailed, ProviderError
from .registry import ProviderRegistry

_LOGGER = logging.getLogger(__name__)


class Router:
    """Routes an operation to the best available provider of a platform."""

    def __init__(self, registry: ProviderRegistry, platform: str) -> None:
        self._registry = registry
        self.platform = platform
        self.last_provider: str | None = None
        self.last_error: str | None = None

    def candidates(self, **capabilities: Any) -> list:
        """Return healthy, capable providers sorted by weight descending."""
        providers = [
            p
            for p in self._registry.providers(self.platform)
            if p.enabled and p.health.available and p.supports(**capabilities)
        ]
        return sorted(providers, key=lambda p: p.weight, reverse=True)

    async def run(self, op: str, *args: Any, **kwargs: Any) -> Any:
        """Try the operation on each candidate until one succeeds.

        ``op`` is the provider method name to call (e.g. ``"transcribe"``).
        Keyword argument ``capabilities`` is consumed by candidate
        filtering and not passed to the provider.
        """
        capabilities = kwargs.pop("capabilities", {})
        errors: dict[str, ProviderError] = {}
        for provider in self.candidates(**capabilities):
            try:
                result = await getattr(provider, op)(*args, **kwargs)
            except ProviderError as err:
                _LOGGER.warning("Provider %s failed: %s", provider.name, err)
                provider.health.record_failure(err)
                errors[provider.name] = err
                self.last_provider = provider.name
                self.last_error = str(err)
                continue
            provider.health.record_success()
            self.last_provider = provider.name
            self.last_error = None
            return result
        raise AllProvidersFailed(errors)

    async def run_stream(self, open_stream: Any, *args: Any, **kwargs: Any) -> Any:
        """Run a streaming operation; reserved for TTS/conversation.

        The streaming commit rule - failover only until the first
        validated chunk is handed to Home Assistant - is implemented here
        once streaming platforms land.
        """
        raise NotImplementedError
