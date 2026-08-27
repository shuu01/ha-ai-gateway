"""OpenAI-compatible STT provider.

Covers Groq, OpenRouter, Mistral, Ollama, LiteLLM, and self-hosted
faster-whisper-server: any backend exposing the OpenAI
``POST /v1/audio/transcriptions`` contract. Uses plain aiohttp over
HA's shared client session so no extra pip dependency is required.
"""

from __future__ import annotations

import asyncio
import json
import logging

import aiohttp
from homeassistant.components import stt
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..errors import (
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderNetworkError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderTimeoutError,
)
from ..provider import Provider

_LOGGER = logging.getLogger(__name__)

TRANSCRIPTION_TIMEOUT_SECONDS = 120
MAX_ERROR_BODY_BYTES = 2048

# Whisper-family languages, same set OpenAI advertises. All OpenAI
# compatible STT backends expose whisper models, so this list is shared.
SUPPORTED_LANGUAGES = [
    "af-ZA",  # Afrikaans
    "ar-SA",  # Arabic
    "hy-AM",  # Armenian
    "az-AZ",  # Azerbaijani
    "be-BY",  # Belarusian
    "bs-BA",  # Bosnian
    "bg-BG",  # Bulgarian
    "ca-ES",  # Catalan
    "zh-CN",  # Chinese (Mandarin)
    "hr-HR",  # Croatian
    "cs-CZ",  # Czech
    "da-DK",  # Danish
    "nl-NL",  # Dutch
    "en-US",  # English
    "et-EE",  # Estonian
    "fi-FI",  # Finnish
    "fr-FR",  # French
    "gl-ES",  # Galician
    "de-DE",  # German
    "el-GR",  # Greek
    "he-IL",  # Hebrew
    "hi-IN",  # Hindi
    "hu-HU",  # Hungarian
    "is-IS",  # Icelandic
    "id-ID",  # Indonesian
    "it-IT",  # Italian
    "ja-JP",  # Japanese
    "kn-IN",  # Kannada
    "kk-KZ",  # Kazakh
    "ko-KR",  # Korean
    "lv-LV",  # Latvian
    "lt-LT",  # Lithuanian
    "mk-MK",  # Macedonian
    "ms-MY",  # Malay
    "mr-IN",  # Marathi
    "mi-NZ",  # Maori
    "ne-NP",  # Nepali
    "no-NO",  # Norwegian
    "fa-IR",  # Persian
    "pl-PL",  # Polish
    "pt-PT",  # Portuguese
    "ro-RO",  # Romanian
    "ru-RU",  # Russian
    "sr-RS",  # Serbian
    "sk-SK",  # Slovak
    "sl-SI",  # Slovenian
    "es-ES",  # Spanish
    "sw-KE",  # Swahili
    "sv-SE",  # Swedish
    "fil-PH",  # Tagalog (Filipino)
    "ta-IN",  # Tamil
    "th-TH",  # Thai
    "tr-TR",  # Turkish
    "uk-UA",  # Ukrainian
    "ur-PK",  # Urdu
    "vi-VN",  # Vietnamese
    "cy-GB",  # Welsh
]


def _classify_http_error(status: int, body_snippet: str = "") -> ProviderError:
    """Map an HTTP status (and optional body) to a typed exception."""
    if status in (401, 403):
        return ProviderAuthError(f"Authentication failed (HTTP {status})")
    if status == 402:
        return ProviderQuotaError(f"Quota exhausted (HTTP {status})")
    if status == 429:
        # 429 is used for BOTH true rate limits and out-of-credits. The
        # body's ``insufficient_quota`` marker disambiguates them.
        if "insufficient_quota" in body_snippet:
            return ProviderQuotaError(
                "Quota exhausted (HTTP 429, insufficient_quota)"
            )
        return ProviderRateLimitError(f"Rate limit hit (HTTP {status})")
    if status >= 500:
        return ProviderServerError(f"Provider server error (HTTP {status})")
    return ProviderError(f"Unexpected provider error (HTTP {status})")


class OpenAICompatibleProvider(Provider):
    """An OpenAI-compatible speech-to-text provider."""

    def __init__(
        self,
        *,
        hass: HomeAssistant,
        unique_id: str,
        name: str,
        platform: str,
        endpoint: str,
        api_key: str | None,
        model: str,
        weight: int,
        prompt: str | None = None,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            unique_id=unique_id,
            name=name,
            platform=platform,
            weight=weight,
            enabled=enabled,
        )
        self._hass = hass
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._prompt = prompt

    @property
    def supported_languages(self) -> list[str]:
        return list(SUPPORTED_LANGUAGES)

    async def transcribe(
        self, metadata: stt.SpeechMetadata, audio: bytes
    ) -> str:
        """Upload the audio and return the transcript text."""
        session = async_get_clientsession(self._hass)
        url = f"{self._endpoint}/v1/audio/transcriptions"

        form = aiohttp.FormData()
        form.add_field("model", self._model)
        form.add_field(
            "file",
            audio,
            filename=f"audio.{metadata.format.value}",
        )
        form.add_field("response_format", "json")
        form.add_field("language", metadata.language.split("-")[0])
        if self._prompt:
            form.add_field("prompt", self._prompt)

        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with session.post(
                url,
                data=form,
                headers=headers,
                timeout=aiohttp.ClientTimeout(
                    total=TRANSCRIPTION_TIMEOUT_SECONDS
                ),
            ) as response:
                body = await response.read()
        except asyncio.TimeoutError as err:
            raise ProviderTimeoutError(
                f"Transcription request timed out: {err}"
            ) from err
        except aiohttp.ClientError as err:
            raise ProviderNetworkError(
                f"Network error during transcription: {err}"
            ) from err

        if response.status >= 400:
            snippet = body[:MAX_ERROR_BODY_BYTES].decode(
                "utf-8", errors="replace"
            )
            raise _classify_http_error(response.status, snippet)

        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as err:
            raise ProviderInvalidResponseError(
                f"Invalid JSON response from provider: {err}"
            ) from err

        text = payload.get("text") if isinstance(payload, dict) else None
        if not text:
            raise ProviderInvalidResponseError(
                "Provider response did not contain a transcript"
            )
        return text
