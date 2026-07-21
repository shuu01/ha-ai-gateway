from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from core.registry import ProviderRegistry
from core.router import Router


class AIGatewayRuntime:
    """Shared runtime state for one AI Gateway config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        self.hass = hass
        self.entry = entry

        self.registry = ProviderRegistry()
        self.router = Router(self.registry)
