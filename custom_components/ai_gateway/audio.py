"""Helpers for generating mock audio."""

from __future__ import annotations

import io
import math
import struct
import wave


def generate_sine_wav(
    *,
    frequency: float = 440.0,
    duration: float = 1.0,
    sample_rate: int = 16000,
    amplitude: float = 0.3,
) -> bytes:
    """Generate a mono 16-bit PCM sine wave."""

    num_samples = int(sample_rate * duration)

    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit PCM
        wav.setframerate(sample_rate)

        frames = bytearray()

        for i in range(num_samples):
            sample = amplitude * math.sin(
                2.0 * math.pi * frequency * i / sample_rate
            )
            pcm = int(sample * 32767)
            frames.extend(struct.pack("<h", pcm))

        wav.writeframes(frames)

    return buffer.getvalue()
