"""Typed provider error hierarchy for AI Gateway.

Every provider failure is raised as a subclass of :class:`ProviderError`
so the router and health tracking can classify failures without string
matching. The concrete class determines the cooldown applied to the
provider (see ``core/health.py``).
"""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for all provider failures."""


class ProviderAuthError(ProviderError):
    """Authentication failed (HTTP 401/403)."""


class ProviderQuotaError(ProviderError):
    """Quota exhausted (HTTP 402, or 429 with an ``insufficient_quota`` marker)."""


class ProviderRateLimitError(ProviderError):
    """Rate limited (HTTP 429)."""


class ProviderServerError(ProviderError):
    """Upstream returned a 5xx server error."""


class ProviderNetworkError(ProviderError):
    """Failed to reach the provider (connection/DNS/network)."""


class ProviderTimeoutError(ProviderError):
    """The request timed out."""


class ProviderInvalidResponseError(ProviderError):
    """The provider returned an unusable response."""


class ProviderConfigError(ProviderError):
    """The provider is unreachable as configured (e.g. HTTP 404).

    Almost always a configuration error: wrong base URL, missing path, or
    a model id the endpoint does not expose. Treated as permanent (like
    auth) until the provider is reconfigured or restarted.
    """


class AllProvidersFailed(ProviderError):
    """Every candidate provider failed.

    Carries the per-provider errors keyed by provider name.
    """

    def __init__(self, errors: dict[str, ProviderError]) -> None:
        self.errors = errors
        detail = ", ".join(f"{name}: {error}" for name, error in errors.items())
        super().__init__(f"All providers failed: {detail}")
