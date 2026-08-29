"""Provider registry: holds every provider for an entry and builds adapters.

Built from config subentries at setup time; the runtime rebuilds it in
place when a subentry is added/reconfigured/deleted (see
:meth:`AIGatewayRuntime.rebuild`).
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant

from ..const import CONF_PROVIDER_TYPE, PROVIDER_TYPE_OPENAI_COMPATIBLE
from .provider import Provider
from .providers.openai_compatible import OpenAICompatibleProvider


def provider_factory(subentry: ConfigSubentry, hass: HomeAssistant) -> Provider:
    """Build the adapter class for a provider subentry."""
    data = subentry.data
    provider_type = data[CONF_PROVIDER_TYPE]
    if provider_type == PROVIDER_TYPE_OPENAI_COMPATIBLE:
        return OpenAICompatibleProvider(
            hass=hass,
            unique_id=subentry.subentry_id,
            name=subentry.title,
            platform=subentry.subentry_type,
            endpoint=data["endpoint"],
            api_key=data.get("api_key"),
            model=data["model"],
            weight=data.get("weight", 1),
            prompt=data.get("prompt"),
        )
    raise ValueError(f"Unknown provider type: {provider_type}")


class ProviderRegistry:
    """Holds the configured providers for one config entry."""

    def __init__(self) -> None:
        self._providers: list[Provider] = []

    def register(self, provider: Provider) -> None:
        """Register a provider in the pool."""
        self._providers.append(provider)

    def providers(self, platform: str) -> list[Provider]:
        """Return all providers for a platform, in registration order."""
        return [p for p in self._providers if p.platform == platform]

    def get(self, provider_id: str) -> Provider | None:
        """Return the provider with the given unique id."""
        return next(
            (p for p in self._providers if p.unique_id == provider_id), None
        )

    def union_languages(self, platform: str) -> list[str]:
        """Return the union of languages of enabled providers, in order."""
        languages: list[str] = []
        for provider in self.providers(platform):
            if not provider.enabled:
                continue
            for language in provider.supported_languages:
                if language not in languages:
                    languages.append(language)
        return languages
