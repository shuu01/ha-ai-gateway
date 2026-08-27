"""Speech-to-text platform for AI Gateway.

A single proxy entity that fans transcription out to the configured
provider pool through the platform's router.
"""

from __future__ import annotations

import io
import logging
import wave
from collections.abc import AsyncIterable

from homeassistant.components import stt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .base import AIGatewayBaseEntity
from .const import MAX_AUDIO_BUFFER_BYTES
from .core.errors import AllProvidersFailed
from .runtime import AIGatewayRuntime

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the AI Gateway STT proxy entity."""
    runtime: AIGatewayRuntime = entry.runtime_data
    if runtime.router("stt") is None:
        return
    async_add_entities([AIGatewaySTTEntity(runtime)])


class AIGatewaySTTEntity(stt.SpeechToTextEntity, AIGatewayBaseEntity):
    """Proxy STT entity routing transcription to the provider pool."""

    _attr_name = "Speech-to-text"

    def __init__(self, runtime: AIGatewayRuntime) -> None:
        super().__init__(entry=runtime.entry)
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_stt"

    @property
    def supported_languages(self) -> list[str]:
        return self._runtime.registry.union_languages("stt")

    @property
    def supported_formats(self) -> list[stt.AudioFormats]:
        return [stt.AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[stt.AudioCodecs]:
        return [stt.AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[stt.AudioBitRates]:
        return [stt.AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[stt.AudioSampleRates]:
        return [stt.AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[stt.AudioChannels]:
        return [stt.AudioChannels.CHANNEL_MONO]

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        router = self._runtime.router("stt")
        return {
            "last_provider": router.last_provider if router else None,
            "last_error": router.last_error if router else None,
        }

    async def async_process_audio_stream(
        self,
        metadata: stt.SpeechMetadata,
        stream: AsyncIterable[bytes],
    ) -> stt.SpeechResult:
        """Buffer the PCM stream and route transcription to the pool."""
        pcm = bytearray()
        for chunk in stream:
            if len(pcm) + len(chunk) > MAX_AUDIO_BUFFER_BYTES:
                _LOGGER.error(
                    "Audio stream exceeds the %d byte buffer cap; aborting",
                    MAX_AUDIO_BUFFER_BYTES,
                )
                return stt.SpeechResult(
                    text=None, result=stt.SpeechResultState.ERROR
                )
            pcm.extend(chunk)

        wav_bytes = _wrap_wav(metadata, bytes(pcm))

        router = self._runtime.router("stt")
        try:
            text = await router.run(
                "transcribe",
                metadata,
                wav_bytes,
                capabilities={"language": metadata.language},
            )
        except AllProvidersFailed as err:
            _LOGGER.error("All STT providers failed: %s", err)
            return stt.SpeechResult(
                text=None, result=stt.SpeechResultState.ERROR
            )

        return stt.SpeechResult(
            text=text, result=stt.SpeechResultState.SUCCESS
        )


def _wrap_wav(metadata: stt.SpeechMetadata, pcm: bytes) -> bytes:
    """Wrap raw PCM frames in a WAV container matching the metadata."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(metadata.channel.value)
        wav.setsampwidth(metadata.bit_rate.value // 8)
        wav.setframerate(metadata.sample_rate.value)
        wav.writeframes(pcm)
    return buffer.getvalue()
