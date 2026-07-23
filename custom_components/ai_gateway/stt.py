"""Mock Speech-to-Text platform."""

from __future__ import annotations

import wave

from collections.abc import AsyncIterable
from functools import partial

from homeassistant.components import stt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .base import AIGatewayBaseEntity
import logging

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ["en-US"]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up AI Gateway STT."""

    async_add_entities([AIGatewaySTTEntity(entry)])

def _write_wav_file(
    path: str,
    metadata: stt.SpeechMetadata,
    audio: bytes,
) -> None:
    """Write audio to a WAV file."""
    with wave.open(path, "wb") as wav:
        wav.setnchannels(metadata.channel.value)
        wav.setsampwidth(metadata.bit_rate.value // 8)
        wav.setframerate(metadata.sample_rate.value)
        wav.writeframes(audio)


class AIGatewaySTTEntity(stt.SpeechToTextEntity, AIGatewayBaseEntity):
    """Mock STT provider."""

    _attr_has_entity_name = True
    _attr_name = "Speech-to-text"

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry

        self._attr_unique_id = f"{entry.entry_id}_stt"

        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="AI Gateway",
            manufacturer="AI Gateway",
            model="Mock",
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    @property
    def supported_languages(self) -> list[str]:
        return SUPPORTED_LANGUAGES

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


    async def async_process_audio_stream(
        self,
        metadata: stt.SpeechMetadata,
        stream: AsyncIterable[bytes],
    ) -> stt.SpeechResult:
        """Mock transcription."""

        audio = bytearray()
        count = 0
        total = 0

        async def proxy_stream() -> AsyncIterable[bytes]:
            nonlocal count, total

            async for chunk in stream:
                audio.extend(chunk)
                count += 1
                total += len(chunk)
                yield chunk

        #
        # TODO:
        # result = await upstream_provider.internal_async_process_audio_stream(
        #     metadata,
        #     proxy_stream(),
        # )
        #
        # For now we simply consume the stream.
        #
        async for _ in proxy_stream():
            pass

        logger.warning(f"Received {count} chunks ({total} bytes)")
        logger.warning(
            f"format={metadata.format}\n"
            f"codec={metadata.codec}\n"
            f"sample_rate={metadata.sample_rate}\n"
            f"bit_rate={metadata.bit_rate}\n"
            f"channels={metadata.channel}"
        )

        await self.hass.async_add_executor_job(
            partial(
                _write_wav_file,
                "/config/test.wav",
                metadata,
                bytes(audio),
            )
        )

        return stt.SpeechResult(
            text="This is a mock transcription.",
            result=stt.SpeechResultState.SUCCESS,
        )
