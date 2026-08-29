"""Shared runtime state for one AI Gateway config entry.

Builds the provider pool from the entry's subentries and exposes a
:class:`Router` per platform (``stt`` today). The registry can be rebuilt
in place on a subentry change without reloading the full entry.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
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
        self._state_listeners: list[Callable[[], None]] = []

        registry = ProviderRegistry()
        self.routers: dict[str, Router] = {}
        self._rebuild(registry, entry.subentries.values())
        self.registry = registry

    def add_state_listener(self, listener: Callable[[], None]) -> None:
        """Register a callback invoked after the registry is rebuilt."""
        self._state_listeners.append(listener)

    def refresh_state(self) -> None:
        """Notify registered listeners (e.g. entities) to rewrite state."""
        for listener in self._state_listeners:
            listener()

    def rebuild(self) -> None:
        """Rebuild the provider registry from the entry's current subentries.

        Re-points the existing routers at the new registry and replaces the
        registry. Idempotent, so concurrent subentry signals are safe. The
        entity stays registered; callers notify it to write state afterwards.
        """
        registry = ProviderRegistry()
        self._rebuild(registry, self.entry.subentries.values())
        self.registry = registry

    def _rebuild(
        self,
        registry: ProviderRegistry,
        subentries: Iterable[ConfigSubentry],
    ) -> None:
        """Build providers into ``registry`` and ensure a router per platform."""
        for subentry in subentries:
            provider = provider_factory(subentry, self.hass)
            registry.register(provider)
            platform = provider.platform
            if platform not in self.routers:
                self.routers[platform] = Router(registry, platform)
        for router in self.routers.values():
            router.update_registry(registry)

    def router(self, platform: str) -> Router | None:
        """Return the router for a platform, or None if no providers exist."""
        return self.routers.get(platform)
