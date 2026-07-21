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
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .base import AIGatewayBaseEntity
from .audio import generate_silence_wav

if TYPE_CHECKING:
    from . import AIGatewayConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: AIGatewayConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up TTS entities."""
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "tts":
            continue

        async_add_entities(
            [AIGatewayTTSEntity(config_entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


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

    def __init__(
        self,
        entry: "AIGatewayConfigEntry",
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the entity."""
        super().__init__(entry, subentry)
        self._attr_name = subentry.title

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
        """Return one second of silent WAV audio."""

        return (
            "wav",
            generate_sine_wav(),
        )
