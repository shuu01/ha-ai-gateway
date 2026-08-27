# AGENTS.md

## What this is

Home Assistant custom component (HACS integration) providing STT, Conversation, and TTS providers with a routing layer. STT is a **real implementation** (provider pool + failover router); Conversation and TTS are still **mocks** — no conversation/TTS AI providers exist yet. `README.md` documents the intended provider set.

- Component root: `custom_components/ai_gateway/` (do not add code outside it)
- Config flow is single-instance (`single_instance_allowed`); providers are configured as **config subentries** (type `stt`)
- `manifest.json` has no `homeassistant` minimum version or pip `requirements`

## Architecture state

- STT is implemented end-to-end (OpenSpec change `stt-provider-pool` in the `private` store; all tasks done except manual HA verification 6.1–6.4):
  - `core/errors.py` — typed exception hierarchy (`ProviderError` + subclasses, `AllProvidersFailed`).
  - `core/health.py` — `ProviderHealth` with per-error-type cooldowns (timeout 120s, network/server/invalid-response 300s, rate-limit/quota 1h, auth permanent `None`); not persisted.
  - `core/provider.py` — abstract `Provider` (identity, `weight`, `enabled`, `supported_languages`/`supported_formats`, `supports()`, abstract `async transcribe(metadata, audio)`).
  - `core/providers/openai_compatible.py` — `OpenAICompatibleProvider` (direct aiohttp multipart POST to `{endpoint}/v1/audio/transcriptions` via HA's shared session, 120s timeout, HTTP-status → typed error mapping).
  - `core/registry.py` — `provider_factory(subentry, hass)` + `ProviderRegistry` (`register`, `providers(platform)`, `get`, `union_languages`).
  - `core/router.py` — `Router(registry, platform)` with `candidates(**capabilities)` (enabled + healthy + `supports`, weight desc, config order tie-break), `async run(op, *args, **kwargs)` (pops `capabilities`; failover; records health; raises `AllProvidersFailed`); `run_stream` is a NotImplementedError placeholder for streaming platforms. `last_provider`/`last_error` are stored on the router.
  - `runtime.py` — `AIGatewayRuntime` builds registry + per-platform routers from `entry.subentries`; `entry.runtime_data` is set in `__init__.py`.
  - `stt.py` — single `AIGatewaySTTEntity` created only when an STT router exists; union languages from registry; canonical contract WAV/PCM/16-bit/16 kHz/mono; buffers PCM (2 MB cap, `MAX_AUDIO_BUFFER_BYTES`), re-wraps WAV, routes via `router.run("transcribe", ...)` filtered by `language`; `last_provider`/`last_error` attributes. Reuses `AIGatewayBaseEntity`.
  - Config entry is **version 2 only**; there is **no `async_migrate_entry`** — stored v1 (mock-era) entries are dropped (fail to load; remove + re-add). `config_flow.py` exposes an STT provider subentry flow (add/reconfigure: provider_type, endpoint, api_key optional, model, weight, prompt) ending in `async_update_reload_and_abort`.
- Remaining mocks to be aware of:
  - `tts.py` returns a generated sine WAV (`audio.generate_sine_wav()`).
  - `conversation.py` returns a random mock string via `_async_handle_message`.
  - Each platform still duplicates its own `dr.DeviceInfo` (STT reuses `base.py`'s `AIGatewayBaseEntity`; `conversation.py`/`tts.py` do not).
  - The OpenAI-compatible STT API is one-shot (no streaming transcription); buffering is required — do not try to stream to `/v1/audio/transcriptions`.

## Development workflow

- Changes are spec-driven via OpenSpec (`schema: spec-driven`). Planning is fully externalized to the registered **`private` store** (`openspec/` in this repo is only a `store: private` pointer; real specs/changes live in `~/openspec/openspec/`). Commands run here resolve to the store automatically. Workflows/skills live in `.github/prompts/` and `.github/skills/` (`opsx-propose`, `opsx-apply`, etc.). The old `.opencode/` copies are deleted — use the `.github/` ones.
- Current change in flight: `stt-provider-pool` (tasks.md 1.1–5.4 done; 6.1–6.4 manual HA verification pending). Implement only tasks from the change's `tasks.md`; update checkboxes as you finish.
- No CI, no tests, no linter/formatter/typecheck config, no `pyproject.toml`/`setup.cfg`. Verification is manual: install by copying `custom_components/ai_gateway` into HA's `custom_components` dir and restart HA.
- If adding a new `strings.json` entry, mirror it in `translations/en.json` (they are currently identical).
- When a config-flow step/abort changes, keep `strings.json`, `translations/en.json`, and `config_flow.py` in sync.
