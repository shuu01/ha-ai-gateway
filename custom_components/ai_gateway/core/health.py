"""Per-provider health tracking with error-type cooldowns.

Health state is intentionally NOT persisted: on restart every provider
starts healthy ("available") and the first request confirms it. A
success clears all failure state. A permanent (auth) failure disables
only that provider - never the gateway.
"""

from __future__ import annotations

import logging
import time

from .errors import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderNetworkError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderTimeoutError,
)

_LOGGER = logging.getLogger(__name__)

# Cooldown in seconds applied after a failure, keyed by error type.
# ``None`` means the provider is disabled until reconfigured or restart.
COOLDOWNS: dict[type[ProviderError], int | None] = {
    ProviderTimeoutError: 120,
    ProviderNetworkError: 300,
    ProviderServerError: 300,
    ProviderInvalidResponseError: 300,
    ProviderRateLimitError: 3600,
    ProviderQuotaError: 3600,
    ProviderAuthError: None,
    ProviderConfigError: None,
}

# Fallback for error types not explicitly listed (e.g. unexpected status).
DEFAULT_COOLDOWN_SECONDS = 300


class ProviderHealth:
    """Tracks the availability of a single provider.

    ``available`` is True unless the provider is mid-cooldown or has been
    permanently disabled by an auth failure.
    """

    def __init__(self) -> None:
        self._available_at: float | None = None
        self._disabled = False
        self._last_error: str | None = None

    @property
    def available(self) -> bool:
        """Return True when the provider is eligible for routing."""
        if self._disabled:
            return False
        if self._available_at is None:
            return True
        return time.monotonic() >= self._available_at

    @property
    def last_error(self) -> str | None:
        """Return the last failure message, if any."""
        return self._last_error

    def record_success(self) -> None:
        """Clear all failure state after a successful request."""
        self._disabled = False
        self._available_at = None
        self._last_error = None

    def record_failure(self, error: ProviderError) -> None:
        """Apply the cooldown for the given failure type."""
        self._last_error = str(error)
        cooldown = COOLDOWNS.get(type(error), DEFAULT_COOLDOWN_SECONDS)
        if cooldown is None:
            self._disabled = True
            self._available_at = None
            _LOGGER.warning(
                "Provider disabled until reconfigured or restart: %s", error
            )
        else:
            self._available_at = time.monotonic() + cooldown
            _LOGGER.warning(
                "Provider cooling down for %ss after failure: %s", cooldown, error
            )
