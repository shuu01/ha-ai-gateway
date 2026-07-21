# AI Gateway

AI Gateway is a Home Assistant integration that provides unified Speech-to-Text (STT), Conversation, and Text-to-Speech (TTS) providers with intelligent routing between local and cloud AI services.

## Features

- Unified STT, Conversation, and TTS providers
- Automatic fallback between providers
- Configurable routing policies
- Mix local and cloud AI services
- Designed for Home Assistant Voice

## Planned providers

### Speech-to-Text

- Groq Whisper
- Faster Whisper
- OpenAI
- OpenRouter
- Custom HTTP providers

### Conversation

- OpenAI
- Gemini
- Ollama
- LiteLLM
- OpenRouter
- Custom OpenAI-compatible APIs

### Text-to-Speech

- OpenAI
- Piper
- ElevenLabs
- Kokoro
- Custom HTTP providers

## Example routing

STT

```
Groq Whisper
    ↓
Faster Whisper
```

Conversation

```
Gemini Flash
    ↓
OpenAI GPT-5
    ↓
Ollama
```

TTS

```
OpenAI
    ↓
Piper
```

## Installation

1. Copy `custom_components/ai_gateway` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**.
4. Search for **AI Gateway**.

## Roadmap

- [ ] Config flow
- [ ] Mock STT provider
- [ ] Mock Conversation provider
- [ ] Mock TTS provider
- [ ] Groq STT
- [ ] Faster Whisper
- [ ] OpenAI Conversation
- [ ] Gemini
- [ ] Ollama
- [ ] OpenAI TTS
- [ ] Piper
- [ ] Configurable routing policies
- [ ] Retries and automatic fallback
- [ ] Provider health monitoring
- [ ] Request caching
- [ ] Diagnostics

## License

MIT
