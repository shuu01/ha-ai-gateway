"""Abstract provider contract for AI Gateway.

Concrete providers describe their capabilities so the router can filter
candidates and implement :meth:`transcribe` for the STT platform. The
class is platform-agnostic so conversation/TTS adapters can reuse it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from homeassistant.components import stt

from .health import ProviderHealth


class Provider(ABC):
    """Base class for a single upstream provider."""

    def __init__(
        self,
        *,
        unique_id: str,
        name: str,
        platform: str,
        weight: int,
        enabled: bool = True,
    ) -> None:
        self.unique_id = unique_id
        self.name = name
        self.platform = platform
        self.weight = weight
        self.enabled = enabled
        self.health = ProviderHealth()

    @property
    @abstractmethod
    def supported_languages(self) -> list[str]:
        """Return the languages this provider can handle."""

    @property
    def supported_formats(self) -> list[stt.AudioFormats]:
        """Return the audio formats this provider accepts."""
        return [stt.AudioFormats.WAV]

    def supports(
        self,
        language: str | None = None,
        format: stt.AudioFormats | None = None,
    ) -> bool:
        """Return True when the provider can serve the requested capability."""
        if language is not None and language not in self.supported_languages:
            return False
        if format is not None and format not in self.supported_formats:
            return False
        return True

    @abstractmethod
    async def transcribe(
        self, metadata: stt.SpeechMetadata, audio: bytes
    ) -> str:
        """Transcribe ``audio`` and return the transcript text.

        Raises a subclass of :class:`ProviderError` on failure.
        """
