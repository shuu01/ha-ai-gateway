"""Constants for the AI Gateway integration."""

DOMAIN = "ai_gateway"

# Provider subentry config keys
CONF_PROVIDER_TYPE = "provider_type"
CONF_ENDPOINT = "endpoint"
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_WEIGHT = "weight"
CONF_PROMPT = "prompt"

# Provider types
PROVIDER_TYPE_OPENAI_COMPATIBLE = "openai_compatible"
PROVIDER_TYPES = [
    PROVIDER_TYPE_OPENAI_COMPATIBLE,
]

# Defaults
DEFAULT_ENDPOINT = "https://api.openai.com/v1"
DEFAULT_MODEL = "whisper-1"
DEFAULT_WEIGHT = 1

# Subentry types
SUBTYPE_STT = "stt"

# ~60s of 16 kHz 16-bit mono PCM audio.
MAX_AUDIO_BUFFER_BYTES = 2 * 1024 * 1024
