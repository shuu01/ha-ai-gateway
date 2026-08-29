## Why

The STT platform is still a mock that just writes audio to `/config/test.wav`. The core value of AI Gateway is a **proxy**: one STT entity in front of a pool of user-configured upstream providers (Groq, Gemini, local faster-whisper) with weighted failover — try the highest-weight provider, fall through on error. That is what users actually need and no HACS integration provides it.

## What Changes

- Providers become **config subentries** on the single gateway entry. Each provider subentry carries its own `{type, endpoint, api_key, model, weight, prompt}`. Provider config lives entirely in subentry flows (add/reconfigure/delete), and changes are applied by rebuilding the in-memory registry in place (no entry reload).
- Implement the placeholder `core/registry.py` and `core/router.py`: a `ProviderRegistry` built from subentries at setup, and a `Router` that does capability-filter → weight-sort → health-gated failover.
- **Replace** the mock STT entity (`stt.py`) with a single `AIGatewaySTTEntity` that buffers the incoming PCM stream, re-wraps it in a WAV container, and routes it through the pool. Only one STT entity is created, regardless of provider count.
- Add a **provider adapter layer**: `OpenAICompatibleProvider` (aiohttp, covers Groq/OpenRouter/Mistral/Ollama/LiteLLM/local faster-whisper-server) is the only adapter in this change. Gemini is a follow-up.
- Add **per-provider health with cooldowns** (timeout 120s, connection 300s, 5xx/invalid-response 300s, rate-limit 1h, quota 1h, auth permanent). One provider's failure never disables the gateway.
- Wire `runtime.py`'s `AIGatewayRuntime` into `__init__.py` (currently `entry.runtime_data = None`) and migrate the config entry version.
- Expose `last_provider` (and `last_error`) as entity attributes for diagnostics.

## Capabilities

### New Capabilities
- `provider-pool`: Provider subentry lifecycle (add/reconfigure/delete via subentry flows), registry construction from subentries, weighted failover router with capability filtering, per-provider health with cooldowns, and diagnostics. Shared core that conversation/TTS will reuse.
- `stt-proxy`: The single exposed STT entity — union language advertising, canonical audio contract (WAV/PCM/16-bit/16 kHz/mono), stream buffering with a safety cap, WAV re-wrapping, routing through the pool, and `last_provider`/`last_error` attributes.

### Modified Capabilities
<!-- None: openspec/specs/ is empty; this is the first change. -->

## Impact

- `custom_components/ai_gateway/stt.py` — rewritten from mock to proxy entity.
- `custom_components/ai_gateway/config_flow.py` — subentry flows, version bump + migration; parent config/options flows stay minimal.
- `custom_components/ai_gateway/__init__.py` — build `AIGatewayRuntime` from subentries, set `runtime_data`.
- `custom_components/ai_gateway/runtime.py` — used for the first time.
- `custom_components/ai_gateway/core/registry.py`, `core/router.py` — placeholders implemented; new `core/provider.py`, `core/health.py`, `core/errors.py`.
- `strings.json` + `translations/en.json` — new subentry flow keys (kept in sync).
- No new pip requirements: uses `aiohttp` (already an HA dependency) + HA's shared client session.
- `manifest.json` — unchanged (no version bump needed for existing fields).
