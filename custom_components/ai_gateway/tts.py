"""Text-to-speech support for AI Gateway."""

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, override
from propcache.api import cached_property

from homeassistant.components.tts import (
    ATTR_PREFERRED_FORMAT,
    ATTR_VOICE,
    TextToSpeechEntity,
    TtsAudioType,
    Voice,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .base import AIGatewayBaseEntity
from .audio import generate_sine_wav


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up AI Gateway TTS."""

    async_add_entities([AIGatewayTTSEntity(entry)])

class AIGatewayTTSEntity(TextToSpeechEntity, AIGatewayBaseEntity):
    """Mock AI Gateway TTS entity."""

    _attr_has_entity_name = False
    _attr_name = "Text-to-speech"

    _attr_supported_languages = ["en-US"]
    _attr_default_language = "en-US"

    _attr_supported_options = [
        ATTR_VOICE,
        ATTR_PREFERRED_FORMAT,
    ]

    _supported_voices = [
        Voice("default", "Default"),
    ]

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry

        self._attr_unique_id = f"{entry.entry_id}_tts"

        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="AI Gateway",
            manufacturer="AI Gateway",
            model="Mock",
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    @callback
    @override
    def async_get_supported_voices(self, language: str) -> list[Voice]:
        """Return supported voices."""
        return self._supported_voices

    @cached_property
    @override
    def default_options(self) -> Mapping[str, Any]:
        """Return default TTS options."""
        return {
            ATTR_VOICE: "default",
            ATTR_PREFERRED_FORMAT: "wav",
        }

    @override
    async def async_get_tts_audio(
        self,
        message: str,
        language: str,
        options: dict[str, Any],
    ) -> TtsAudioType:
        """Return one second of sine WAV audio."""

        return (
            "wav",
            generate_sine_wav(),
        )
