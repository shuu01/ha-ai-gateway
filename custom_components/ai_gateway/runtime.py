"""Shared runtime state for one AI Gateway config entry.

Builds the provider pool from the entry's subentries and exposes a
:class:`Router` per platform (``stt`` today).
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .core.registry import ProviderRegistry, provider_factory
from .core.router import Router


class AIGatewayRuntime:
    """Registry + routers for a single AI Gateway config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        self.hass = hass
        self.entry = entry

        self.registry = ProviderRegistry()
        self.routers: dict[str, Router] = {}

        for subentry in entry.subentries.values():
            provider = provider_factory(subentry, hass)
            self.registry.register(provider)
            if provider.platform not in self.routers:
                self.routers[provider.platform] = Router(
                    self.registry, provider.platform
                )

    def router(self, platform: str) -> Router | None:
        """Return the router for a platform, or None if no providers exist."""
        return self.routers.get(platform)
